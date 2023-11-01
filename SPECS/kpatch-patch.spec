# Set to 1 if building an empty subscription-only package.
%define empty_package		0

#######################################################
# Only need to update these variables and the changelog
%define kernel_ver	4.18.0-348.7.1.el8_5
%define kpatch_ver	0.9.5
%define rpm_ver		1
%define rpm_rel		3

%if !%{empty_package}
# Patch sources below. DO NOT REMOVE THIS LINE.
#
# https://bugzilla.redhat.com/2034875
Source100: CVE-2021-4155.patch
#
# https://bugzilla.redhat.com/2040593
Source101: CVE-2022-0185.patch
#
# https://bugzilla.redhat.com/2031991
Source102: CVE-2021-0920.patch
#
# https://bugzilla.redhat.com/2034618
Source103: CVE-2021-4154.patch
#
# https://bugzilla.redhat.com/2044377
Source104: CVE-2022-0330.patch
#
# https://bugzilla.redhat.com/2050135
Source105: CVE-2022-0435.patch
#
# https://bugzilla.redhat.com/2052187
Source106: CVE-2022-0492.patch
#
# https://bugzilla.redhat.com/2047620
Source107: CVE-2022-22942.patch
#
# https://bugzilla.redhat.com/2033364
Source108: CVE-2021-4028.patch
#
# https://bugzilla.redhat.com/2056875
Source109: CVE-2022-25636.patch
# End of patch sources. DO NOT REMOVE THIS LINE.
%endif

%define sanitized_rpm_rel	%{lua: print((string.gsub(rpm.expand("%rpm_rel"), "%.", "_")))}
%define sanitized_kernel_ver   %{lua: print((string.gsub(string.gsub(rpm.expand("%kernel_ver"), '.el8_?\%d?', ""), "%.", "_")))}
%define kernel_ver_arch        %{kernel_ver}.%{_arch}

Name:		kpatch-patch-%{sanitized_kernel_ver}
Version:	%{rpm_ver}
Release:	%{rpm_rel}%{?dist}

%if %{empty_package}
Summary:	Initial empty kpatch-patch for kernel-%{kernel_ver_arch}
%else
Summary:	Live kernel patching module for kernel-%{kernel_ver_arch}
%endif

Group:		System Environment/Kernel
License:	GPLv2
ExclusiveArch:	x86_64 ppc64le

Conflicts:	%{name} < %{version}-%{release}

Provides:	kpatch-patch = %{kernel_ver_arch}
Provides:	kpatch-patch = %{kernel_ver}

%if !%{empty_package}
Requires:	systemd
%endif
Requires:	kpatch >= 0.6.1-1
Requires:	kernel-uname-r = %{kernel_ver_arch}

%if !%{empty_package}
BuildRequires:	patchutils
BuildRequires:	kernel-devel = %{kernel_ver}
BuildRequires:	kernel-debuginfo = %{kernel_ver}

# kernel build requirements, generated from:
#   % rpmspec -q --buildrequires kernel.spec | sort | awk '{print "BuildRequires:\t" $0}'
# with arch-specific packages moved into conditional block
BuildRequires:	asciidoc audit-libs-devel bash bc binutils binutils-devel bison bzip2 diffutils elfutils elfutils-devel findutils flex gawk gcc gettext git gzip hmaccalc hostname kmod m4 make ncurses-devel net-tools newt-devel numactl-devel openssl openssl-devel patch pciutils-devel perl-Carp perl-devel perl(ExtUtils::Embed) perl-generators perl-interpreter python3-devel python3-docutils redhat-rpm-config rpm-build sh-utils tar xmlto xz xz-devel zlib-devel java-devel kabi-dw

%ifarch x86_64
BuildRequires:	pesign >= 0.10-4
%endif

%ifarch ppc64le
BuildRequires:	gcc-plugin-devel
%endif

Source0:	https://github.com/dynup/kpatch/archive/v%{kpatch_ver}.tar.gz

Source10:	kernel-%{kernel_ver}.src.rpm

# kpatch-build patches

%global _dupsign_opts --keyname=rhelkpatch1

%define builddir	%{_builddir}/kpatch-%{kpatch_ver}
%define kpatch		%{_sbindir}/kpatch
%define kmoddir 	%{_usr}/lib/kpatch/%{kernel_ver_arch}
%define kinstdir	%{_sharedstatedir}/kpatch/%{kernel_ver_arch}
%define patchmodname	kpatch-%{sanitized_kernel_ver}-%{version}-%{sanitized_rpm_rel}
%define patchmod	%{patchmodname}.ko

%define _missing_build_ids_terminate_build 1
%define _find_debuginfo_opts -r
%undefine _include_minidebuginfo
%undefine _find_debuginfo_dwz_opts

%description
This is a kernel live patch module which can be loaded by the kpatch
command line utility to modify the code of a running kernel.  This patch
module is targeted for kernel-%{kernel_ver}.

%prep
%autosetup -n kpatch-%{kpatch_ver} -p1

%build
kdevdir=/usr/src/kernels/%{kernel_ver_arch}
vmlinux=/usr/lib/debug/lib/modules/%{kernel_ver_arch}/vmlinux

# kpatch-build
make -C kpatch-build

# patch module
for i in %{sources}; do
	[[ $i == *.patch ]] && patch_sources="$patch_sources $i"
done
export CACHEDIR="%{builddir}/.kpatch"
kpatch-build/kpatch-build --non-replace -n %{patchmodname} -r %{SOURCE10} -v $vmlinux --skip-cleanup $patch_sources || { cat "${CACHEDIR}/build.log"; exit 1; }


%install
installdir=%{buildroot}/%{kmoddir}
install -d $installdir
install -m 755 %{builddir}/%{patchmod} $installdir


%files
%{_usr}/lib/kpatch


%post
%{kpatch} install -k %{kernel_ver_arch} %{kmoddir}/%{patchmod}
chcon -t modules_object_t %{kinstdir}/%{patchmod}
sync
if [[ %{kernel_ver_arch} = $(uname -r) ]]; then
	cver="%{rpm_ver}_%{rpm_rel}"
	pname=$(echo "kpatch_%{sanitized_kernel_ver}" | sed 's/-/_/')

	lver=$({ %{kpatch} list | sed -nr "s/^${pname}_([0-9_]+)\ \[enabled\]$/\1/p"; echo "${cver}"; } | sort -V | tail -1)

	if [ "${lver}" != "${cver}" ]; then
		echo "WARNING: at least one loaded kpatch-patch (${pname}_${lver}) has a newer version than the one being installed."
		echo "WARNING: You will have to reboot to load a downgraded kpatch-patch"
	else
		%{kpatch} load %{patchmod}
	fi
fi
exit 0


%postun
%{kpatch} uninstall -k %{kernel_ver_arch} %{patchmod}
sync
exit 0

%else
%description
This is an empty kpatch-patch package which does not contain any real patches.
It is only a method to subscribe to the kpatch stream for kernel-%{kernel_ver}.

%files
%doc
%endif

%changelog
* Tue Apr 19 2022 Yannick Cote <ycote@redhat.com> [1-3.el8_5]
- kernel: heap out of bounds write in nf_dup_netdev.c [2056875] {CVE-2022-25636}
- kernel: use-after-free in RDMA listen() [2033364] {CVE-2021-4028}

* Fri Mar 04 2022 Yannick Cote <ycote@redhat.com> [1-2.el8_5]
- kernel: failing usercopy allows for use-after-free exploitation [2047620] {CVE-2022-22942}
- kernel: cgroups v1 release_agent feature may allow privilege escalation [2052187] {CVE-2022-0492}
- kernel: remote stack overflow via kernel panic on systems using TIPC may lead to DoS [2050135] {CVE-2022-0435}
- kernel: possible privileges escalation due to missing TLB flush [2044377] {CVE-2022-0330}
- kernel: local privilege escalation by exploiting the fsconfig syscall parameter leads to container breakout [2034618] {CVE-2021-4154}
- kernel: Use After Free in unix_gc() which could result in a local privilege escalation [2031991] {CVE-2021-0920}

* Tue Jan 18 2022 Joe Lawrence <joe.lawrence@redhat.com> [1-1.el8_5]
- kernel: fs_context: heap overflow in legacy parameter handling [2040593] {CVE-2022-0185}
- kernel: xfs: raw block device data leak in XFS_IOC_ALLOCSP IOCTL [2034875] {CVE-2021-4155}

* Tue Dec 14 2021 Yannick Cote <ycote@redhat.com> [0-0.el8]
- An empty patch to subscribe to kpatch stream for kernel-4.18.0-348.7.1.el8_5 [2032436]
