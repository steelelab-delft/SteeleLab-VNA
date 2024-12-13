# Server

The server software for the Red Pitaya STEMlab 125-14 has been designed and tested in Python 3.10.4,
which is available by default in the used operating system. You can use the provided [image](http://gofile.me/4Gvxj/FV2TsLOm6)
that has everything pre-installed.
- Connect the Red Pitaya board via ethernet and power it on.
- The Python server will automatically start.
- DHCP is enabled by default. Find the IP address of the Red Pitaya board in the list
  of connected devices in your router.
- Change the `ADDR_RP` variable to the correct IP address in [simple_api_usage.ipynb](../example/simple_api_usage.ipynb).

## Steps for manual installation

- Download the Red Pitaya PYNQ OS image (Pynq-Redpitaya-125-14-3.0.1.img) from [this repository](https://github.com/dspsandbox/Pynq-Redpitaya-125).
- Flash the image to a micro SD card (&ge; 16 GB recommended) with your favorite flashing tool.
- Insert the micro SD card into the Red Pitaya board.
- Attach an ethernet cable to the board; use a switch / router or connect it directly to the client pc.
- Power on the board. The green status led should turn on.
- If you connect the board directly via an ethernet cable to the client pc, the IP address is 192.168.2.99.
  Otherwise, find the IP address through your router. In both cases the hostname is `pynq`. For more information, see the
  [Pynq documentation](https://pynq.readthedocs.io/en/v2.6.1/appendix.html#assign-your-computer-a-static-ip-address).
- Login via SSH with default user `xilinx` and password `xilinx`.
- (Optional) configure the network settings on the Red Pitaya board according to your network setup (in /etc/network/inferfaces.d/eth0).
- Clone this repository to `/home/xilinx/slvna` using the command
  ```bash
  git clone --depth 1 https://github.com/SteeleLab/SLVNA.git /home/xilinx/slvna
  ```
- Download the hardware overlay files (.bit and .hwh) from the GitHub [releases](https://github.com/steelelab-delft/SteeleLab-VNA/releases/) page. For the current release the commands are the following:
  ```bash
  wget https://github.com/steelelab-delft/SteeleLab-VNA/releases/download/v1.0/slvna_v1_0.bit -O /home/xilinx/bit/vna_v1_0.bit
  wget https://github.com/steelelab-delft/SteeleLab-VNA/releases/download/v1.0/slvna_v1_0.hwh -O /home/xilinx/bit/vna_v1_0.hwh
  ```
  (Note that the version should match the version in [protocol.py](../../project/server/protocol.py)).
- (Optional): install 'bc' to be able to measure the Red Pitaya's cpu temperature: `sudo apt update && sudo apt install bc`.
- Run the [server start script](../../project/server/sh/start_vna_server.sh) as root.
  **Note**: do not use `sudo bash start_vna_server`, but first switch to root `sudo su` and then enter `bash start_vna_server`.
- You can test if the server has started correctly by running `nc localhost 2024` via SSH, then typing `d` and `ctrl+d`.
  If a question mark appears, the server has succesfully started.

## Starting automatically

Ultimately, starting the server can be done automatically via a cron job.
This job has to be executed as `root` since PYNQ will not work otherwise.
The easiest way to do this is by updating the crontab of `root` with the command
```bash
sudo crontab -e -u root
```
and adding this line to it:
```cron
* * * * * bash /home/xilinx/slvna/project/server/sh/start_vna_server.sh >> /home/xilinx/slvna/vna_server.log 2>&1
```
This tries starting the server every single minute if not yet started and saves logs in the vna_server.log file.

## Jupyter server

If you want to experiment or debug with PYNQ, the Red Pitaya's Jupyter server is useful.
Go in your browser to `http://[redpitaya-ip]:9090` (replace [redpitaya-ip] with the correct IP address).
The Jupyter kernel has the PYNQ Python library pre-installed, as well as other libraries like NumPy.
The password is `xilinx`.

**Note**: be careful that the Jupyter kernel does not interfere with the SLVNA Python server.
Before running any notebook where the PYNQ libary is used, the SLVNA Python server has to be stopped.
It starts every minute unless you edit root's crontab (via SSH) with `crontab -e -u root`
and comment the entry with start_vna_server.sh. To stop the Python server manually,
run via SSH `nc localhost 2024`, then type ! followed by ctrl + d and finally ctrl + c.
Also make sure the Red Pitaya has a clock signal (either external or internal), otherwise
the DMA request will hang.
