# OpenWRT-Industrial-Router

A Python-based system designed to run on **OpenWRT** for industrial routers. It provides secure TCP/IP access (via Ethernet, Internet, and cellular networks) to the internal network and serial ports (**RS232** / **RS485**), with support for remote command execution and a web-based configuration interface.

## Overview

This project turns an OpenWRT-powered industrial router into a flexible gateway that bridges:

- External networks (Ethernet, WAN/Internet, cellular/4G/5G)
- Internal LAN
- Serial devices connected via RS232 and/or RS485

It is intended for industrial IoT, SCADA, remote equipment monitoring, and automation scenarios where reliable remote access to serial devices and the local network is required.

## Features

- **Multi-path connectivity**
  - Ethernet (LAN/WAN)
  - Internet (WAN)
  - Cellular network (modem support)
- **Serial port gateway**
  - RS232 and/or RS485 support
  - TCP-to-serial bridging
  - Configurable baud rate, parity, stop bits, flow control
- **Remote command reception**
  - Accept and execute authorized remote commands
  - Secure command channel (authentication supported)
- **Web-based configuration**
  - Modern web UI for system settings
  - Serial port configuration
  - Network and gateway parameters
  - User management and security settings
- **Designed for OpenWRT**
  - Lightweight Python implementation
  - Compatible with common industrial router hardware running OpenWRT

## Requirements

### Hardware
- Industrial router / gateway running OpenWRT
- Ethernet interface(s)
- Optional: cellular modem (USB or built-in)
- Serial ports (RS232 and/or RS485) or USB-to-serial adapters

### Software
- OpenWRT (recommended recent stable release)
- Python 3.8+ (or the version available in your OpenWRT packages)
- Required Python packages (see `requirements.txt`)

## Installation

1. **Clone the repository** on your development machine or directly on the router (if space and tools allow):

   ```bash
   git clone https://github.com/your-username/openwrt-industrial-gateway.git
   cd openwrt-industrial-gateway
   ```

2. **Install dependencies** on the OpenWRT device:

   ```bash
   opkg update
   opkg install python3 python3-pip
   pip3 install -r requirements.txt
   ```

3. **Copy the application** to a suitable location (e.g. `/opt/gateway` or `/usr/local/gateway`).

4. **Configure** the system (see Configuration section).

5. **Enable and start** the service (example using procd or a simple init script).

## Configuration

Configuration can be done via:

- Web interface (preferred)
- Configuration file (YAML/JSON – location defined by the application)

Typical settings include:

| Setting              | Description                                      |
|----------------------|--------------------------------------------------|
| Serial ports         | Device paths, baud rate, parity, stop bits       |
| TCP listen ports     | Ports for serial-over-TCP and command interface  |
| Network interfaces   | Which interfaces are used for external access    |
| Authentication       | Users, passwords, API keys, or certificates      |
| Cellular             | APN, PIN, modem device (if applicable)           |


## Security Considerations

- Replace all occurrences of "yourgateway.com" with your own gateway URL
- Replace all occurrences of "yourupdatesite.com" with your own firmware update server URL

## Contributing

Contributions are welcome. Please open an issue first to discuss major changes.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenWRT Project
- Python community
- Industrial IoT and serial communication libraries

---

**Disclaimer**: This software is provided as-is for industrial and research use. Ensure compliance with local regulations and security best practices when deploying on production networks.
