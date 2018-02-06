import socket
import http.client
import ssl
import threading
#from urllib.request import Request, urlopen
import struct
import json
import base64
import os
from django.db import transaction
from Utils.models import Lock

class HashcatAPI(object):

    def __init__(self, ip, port, username, password):
        self.ip = ip
        self.port = port
        self.key = base64.b64encode(("%s:%s" % (username, password)).encode("ascii")).decode("ascii")

    def get_hashcat_info(self):
        return self.send("/hashcatInfo")

    def create_dictionary_session(self, session_name, hashfile, rule, wordlist):
        hashfile_path = os.path.join(os.path.dirname(__file__), "..", "Files", "Hashfiles", hashfile.hashfile)

        from Utils.hashcat import Hashcat
        from Hashcat.models import Hashfile

        with transaction.atomic():
            # Prevent hashfile from being modified while read 
            hashfile_lock = Lock.objects.select_for_update().filter(hashfile_id=hashfile.id, lock_ressource="hashfile")[0]

            hashes = open(hashfile_path).read()

            del hashfile_lock

        payload = {
            "name": session_name,
            "crack_type": "dictionary",
            "hash_mode_id": hashfile.hash_type,
            "rule": rule,
            "wordlist": wordlist,
            "hashes": hashes,
            "username_included": False,
        }

        return self.send("/createSession", data=payload)

    def create_mask_session(self, session_name, hashfile, mask):
        hashfile_path = os.path.join(os.path.dirname(__file__), "..", "Files", "Hashfiles", hashfile.hashfile)

        from Utils.hashcat import Hashcat
        from Hashcat.models import Hashfile

        # lock
        with transaction.atomic():
            # Prevent hashfile from being modified while read 
            hashfile_lock = Lock.objects.select_for_update().filter(hashfile_id=hashfile.id, lock_ressource="hashfile")[0]

            hashes = open(hashfile_path).read()

            del hashfile_lock

        payload = {
            "name": session_name,
            "crack_type": "mask",
            "hash_mode_id": hashfile.hash_type,
            "mask": mask,
            "hashes": hashes,
            "username_included": False,
        }

        return self.send("/createSession", data=payload)


    def action(self, session_name, action):
        payload = {
            "session": session_name,
            "action": action,
        }

        return self.send("/action", data=payload)

    def get_session_info(self, session_name):
        return self.send("/sessionInfo/%s" % session_name)

    def remove(self, session_name):
        return self.send("/removeSession/%s" % session_name)

    def get_cracked_file(self, session_name):
        return self.send("/cracked/%s" % session_name)

    def get_hashcat_output(self, session_name):
        return self.send("/hashcatOutput/%s" % session_name)

    def get_hashes(self, session_name):
        return self.send("/hashes/%s" % session_name)

    def get_potfile(self, session_name, from_line):
        return self.send("/getPotfile/%s/%d" % (session_name, from_line))

    def upload_rule(self, name, rule_file):
        payload = {
            "name": name,
            "rules": base64.b64encode(rule_file).decode(),
        }

        return self.send("/uploadRule", data=payload)

    def upload_mask(self, name, mask_file):
        payload = {
            "name": name,
            "masks": base64.b64encode(mask_file).decode(),
        }

        return self.send("/uploadMask", data=payload)

    def upload_wordlist(self, name, wordlist_file):
        payload = {
            "name": name,
            "wordlists": base64.b64encode(wordlist_file).decode(),
        }

        return self.send("/uploadWordlist", data=payload)

    def send(self, url, data=None):
        headers = {
            "Content-Type": "text/plain; charset=utf-8",
            "Accept-Encoding": "text/plain",
            "Authorization": "Basic %s" % self.key,
        }

        gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)  # disable certif validation
        conn = http.client.HTTPSConnection(self.ip, self.port, context=gcontext)

        if data == None:
            conn.request("GET", url, headers=headers)
        else:
            conn.request("POST", url, "%s\r\n\r\n" % json.dumps(data), headers)

        res = conn.getresponse()

        data = res.read()

        conn.close()
        return json.loads(data.decode("ascii"))

