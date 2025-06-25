%define name ServiceReport
%define version 2.2.4
%define release 1

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
Requires: %{python} systemd

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

* Fri Nov 15 2019 Sourabh Jain <sourabhjain@linux.ibm.com> 2.2.1
- First Open source release
- Initial Commit of Open Source release
