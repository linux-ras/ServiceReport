# ServiceReport

ServiceReport is a tool to validate and repair system configuration for
specific purposes. Initially envisaged to help setup systems for correctly
First Failure Data Capture (FFDC), it has now morphed into a plugin based
framework which can do more than just FFDC validation.

One example is the package plugin - which validates if one or a set of
packages is installed or not.

ServiceReport is designed to run in two modes - validate and repair. In the
validate phase, it runs a set of configured plugins to validate if the
requisite checks (package install, daemon config, etc) pass and flags errors
found to syslog. In the repair phase, if the system is configured correctly
to contact the appropriate repos, ServiceReport fixes the issues found in
the validate phase.

The initial Open Source release of ServiceReport caters to all manners of
Power platforms running Linux. It validates the FFDC setup for the
particular instance of Linux on Power (whether running on a PowerVM LPAR,
or Baremetal or as a KVM guest). It also validates the dump configuration
(kdump/fadump) and flags errors as found. The repair action fixes all
errors found in the validate phase, including any crashkernel memory
reservation issues for dumping, updating the bootloader config,
regenerating initramfs files, etc. A further feature of ServiceReport is
that it can trigger a dummy crash dump to validate the setup for dumping.

The plugin nature of ServiceReport lends itself to be useful for any
platform on any architecture running Linux. Anything scriptable can be
a plugin - a workload specific setup can be a workload-plugin.


## Getting Started

### Prerequisites

```
python
```

### Installing

#### Using Source Code

Clone the source code
```
git clone https://github.com/linux-ras/ServiceReport
```

Build the project
```
make build
```

Install the project
```
make install
```

### Running

Runs and print the status of all the applicable plugins in current system
```
$ servicereport
```

List all the applicable plugins
```
$ servicereport -l
```

Runs all the applicable plugins to current system and print the detailed status of each plugin
```
$ servicereport -v
```

Runs only P1 and P2 plugins if applicable
```
$ servicereport -p P1 P2
```

Prints the manual page
```
$ man servicereport
```

Repair the incorrect configuration after the validation.
```
$ servicereport -r
```

## Note:
Kdump: ServiceReport does not verify the remote dump location. If the configured dump location
       is remote, please make sure that the remote machine is accessible and has sufficient
       storage to store the dump.

Repair: The auto-fix functionality is only available for package, daemon, kdump, and Fadump.

## TODO
Auto-repair plugins for HTX.

## Bug Reporting and Feature Request
https://github.com/linux-ras/ServiceReport/issues

## Authors

* **Sourabh Jain** - <sourabhjain@linux.ibm.com>

## Contributors

* **Srikanth Aithal** - <sraithal@linux.vnet.ibm.com>
