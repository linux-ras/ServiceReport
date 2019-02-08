# ServiceReport

ServiceReport is a tool to validate and repair the system configuration.
ServiceReport is a plugin based framework where different plugins performs
different types of validation. For an example, the package plugin validates
whether a certain packages are installed in the system or not. The another
useful feature of this tool is, it validates the First Failure Data Capture (FFDC)
configuration and help users to fix the incorrect configuration automatically.

## Getting Started

### Prerequisites

```
python
```

### Installing

#### Using Source Code

Clone the source code
```
git clone https://github.com/power-ras/ServiceReport
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
https://github.com/power-ras/ServiceReport/issues

## Authors

* **Sourabh Jain** - <sourabhjain@linux.ibm.com>

## Contributors

* **Srikanth Aithal** - <sraithal@linux.vnet.ibm.com>
