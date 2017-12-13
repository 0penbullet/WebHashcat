# WebHashcat
Hashcat web interface

WebHashcat is a very simple but efficient web interface for hashcat password cracking tool.
It hash the following features:
* Distributed cracking sessions between multiple server (you only need to install HashcatNode on the remote server)
* Cracked hashes are displayed as soon as they are cracked
* Analytics

Currently WebHashcat supports rule-based and mask-based attack mode

This project is composed of 2 parts: 
- WebHashcat, the web interface made with the django framework 
- HashcatNode, A hashcat wrapper with creates an API over hashcat

## Install

### HashcatNode

Rename the settings.ini.sample file to settings.ini and fill the parameters accordingly.

The rules, mask and wordlist directory must be writable by the user running hashcatnode

the hashcatnode can be run simply by running `./hashcatnode.py`

### WebHashcat

To be done

## Dependencies

- python3
- django
- flask
- flask-basicauth
- hashcat >= 3
