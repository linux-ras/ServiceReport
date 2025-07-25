%define name ServiceReport
%define version 2.2.5
%define release 2

# By default python 3 is used to build the package.
%define python python3

Name: %{name}
Summary: A tool to validate and repair First Failure Data Capture (FFDC) configuration
Version: %{version}
Release: %{release}
Source0: https://github.com/linux-ras/%{name}/archive/v%{version}/%{name}-%{version}.tar.gz
License: GPLv2+
Group: System/RAS
URL: https://github.com/linux-ras/ServiceReport

# Restricting the package build for ppc64 architecture, update the BuildArch
# tag to build the package for different architecture.
BuildArch: ppc64le
Vendor: IBM Corp.
BuildRequires: %{python} systemd
BuildRequires: %{python}-setuptools
BuildRequires: %{python}-devel
Requires: %{python} systemd
Requires: %{python}-pyudev

%description
ServiceReport is a python based tool that investigates the incorrect First Failure Data
Capture (FFDC) configuration and optionally repairs the incorrect configuration

%define debug_package %{nil}
%prep
%setup -q

%build
%{python} setup.py build

%install
%{python} setup.py install --root=$RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/%{python3_sitelib}/sos/report/plugins
install -m 644 sos-plugin/spyre-external.py $RPM_BUILD_ROOT/%{python3_sitelib}/sos/report/plugins

%post
systemctl enable servicereport.service
systemctl start servicereport.service

%files
%defattr(-,root,root)
%doc /usr/share/man/man8/*
%doc /usr/share/doc/*
%doc /usr/share/licenses/*
/usr/lib/*
/usr/bin/*

%changelog

* Fri Jul 8 2025 Sourabh Jain <sourabhjain@linux.ibm.com> 2.2.5.2
- Do not enable Spyre plugin if card is not present

* Tue Jul 8 2025 Sourabh Jain <sourabhjain@linux.ibm.com> 2.2.5-1
- New plugin to validate and repair spyre configuration
- Remove PrivateDevices from ServiceReprot service
- Remove type=oneshot from ServiceReport service
- Couple of bug fixes in spyre plugin
- sos report plugin to collect spyre data
- Change to include sos report plugin in to rpm

* Fri Nov 15 2019 Sourabh Jain <sourabhjain@linux.ibm.com> 2.2.1
- First Open source release
- Initial Commit of Open Source release
