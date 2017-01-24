#!/usr/bin/python3
import os
import sys
import traceback
import json
import ssl
import datetime
import random
import string

import socketserver
import base64
from flask import Flask, request, abort, send_file
from flask_basicauth import BasicAuth
from io import BytesIO, StringIO

from hashcat import Hashcat

class Server:
    def __init__(self, host, port, user, password, hash_directory):
        self._host = host
        self._port = port
        self._app = Flask(__name__)
        self._route()

        self._app.config['BASIC_AUTH_FORCE'] = True
        self._app.config['BASIC_AUTH_USERNAME'] = user
        self._app.config['BASIC_AUTH_PASSWORD'] = password

        self.user = user
        self.password = password

        self.hash_directory = hash_directory

    def _route(self):
        self._app.add_url_rule("/hashcatInfo", "hashcatInfo", self._hashcatInfo, methods=["GET"])
        self._app.add_url_rule("/sessionInfo/<session_name>", "sessionInfo", self._sessionInfo, methods=["GET"])
        self._app.add_url_rule("/cracked/<session_name>", "cracked", self._cracked, methods=["GET"])
        self._app.add_url_rule("/createSession", "createSession", self._createSession, methods=["POST"])
        self._app.add_url_rule("/removeSession/<session_name>", "removeSession", self._removeSession, methods=["GET"])
        self._app.add_url_rule("/action", "action", self._action, methods=["POST"])
        self._app.add_url_rule("/uploadRule", "uploadRule", self._upload_rule, methods=["POST"])
        self._app.add_url_rule("/uploadMask", "uploadMask", self._upload_mask, methods=["POST"])
        self._app.add_url_rule("/uploadWordlist", "uploadWordlist", self._upload_wordlist, methods=["POST"])

    def start_server(self):
        base_dir = os.path.dirname(__file__)
        context = (base_dir + '/server.crt', base_dir + '/server.key')
        self._app.run(host=self._host, port=self._port, ssl_context=context, threaded=True)

    """
        Returns a json containing the following informations about the running hashcat process:
            - Version
            - Hash types supported
            - Available rules
            - Available masks
            - Available wordlists
            - Sessions :
                - Name
                - Status
                - Cracking type (rules, mask)
                - % cracked
                - % progress
    """
    def _hashcatInfo(self):
        try:
            hash_types = list(Hashcat.hash_modes.values())
            rules = list(Hashcat.rules.keys())
            masks = list(Hashcat.masks.keys())
            wordlists = list(Hashcat.wordlists.keys())
            sessions = []
            for session in Hashcat.sessions.values():
                sessions.append({
                    "name": session.name,
                    "status": session.session_status,
                    "crack_type": session.crack_type,
                    "cracked": (int(session.current_cracked)*100)/int(session.total_hashes),
                    "progress": session.progress,
                })

            result = {
                "response": "ok",
                "version": Hashcat.version,
                "hash_types": hash_types,
                "rules": rules,
                "masks": masks,
                "sessions": sessions,
                "wordlists": wordlists,
            }

            return json.dumps(result)
        except Exception as e:
            traceback.print_exc()

            return json.dumps({
                "response": "error",
                "message": str(e),
            })

    """
        Returns information about a specific session :
            - Name
            - Cracking type (rule, mask)
            - Status
            - Time started
            - Estimated time (rule based attack only)
            - Speed
            - Recovered
            - Progress (%)
            - Cracked hashes (results)
            - Top 10 passwords cracked
            - Password lengths
            - Password charsets
    """
    def _sessionInfo(self, session_name):
        try:

            result = Hashcat.sessions[session_name].details()
            result["response"] = "ok"

            return json.dumps(result)
        except Exception as e:
            traceback.print_exc()

            return json.dumps({
                "response": "error",
                "message": str(e),
            })

    """
        Returns the cracked passwords
    """
    def _cracked(self, session_name):
        try:
            cracked = Hashcat.sessions[session_name].cracked()

            return json.dumps({
                "response": "ok",
                "cracked": cracked,
            })
        except Exception as e:
            traceback.print_exc()

            return json.dumps({
                "response": "error",
                "message": str(e),
            })


    """
        Create a new session, the input should be the following :
            - name: name of the session
            - crack_type: rule or mask
            - hashes: hashes to crack
            - hash_mode_id: hash type
            - wordlist: wordlist file to use (if rule-based attack)
            - rule: rule file to use (if rule-based attack)
            - mask: mask file to use (if mask-based attack)
            - username_included: is the username before the hashes ? (True/False)
    """
    def _createSession(self):
        try:
            data = json.loads(request.data.decode())

            random_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12))
            hash_file = os.path.join(self.hash_directory, data["name"]+"_"+random_name+".list")

            f = open(hash_file, "w")
            f.write(data["hashes"])
            f.close()

            Hashcat.create_session(
                data["name"],
                data["crack_type"],
                hash_file,
                int(data["hash_mode_id"]),
                data["wordlist"] if "wordlist" in data else None,
                data["rule"] if "rule" in data else None,
                data["mask"] if "mask" in data else None,
                data["username_included"]
            )

            res = {"response": "ok"}

            return json.dumps(res)
        except Exception as e:
            traceback.print_exc()

            return json.dumps({
                "response": "error",
                "message": str(e),
            })

    """
        Delete a session
    """
    def _removeSession(self, session_name):
        try:
            Hashcat.remove_session(session_name)

            res = {"response": "ok"}

            return json.dumps(res)
        except Exception as e:
            traceback.print_exc()

            return json.dumps({
                "response": "error",
                "message": str(e),
            })

    """
        Send an action to a session:
        Parameters are :
            - session: session name
            - action: start, update, pause, resume or quit
    """
    def _action(self):
        try:
            data = json.loads(request.data.decode())

            if data["action"] == "start":
                Hashcat.sessions[data["session"]].start()
            if data["action"] == "update":
                Hashcat.sessions[data["session"]].update()
            if data["action"] == "pause":
                Hashcat.sessions[data["session"]].pause()
            if data["action"] == "resume":
                Hashcat.sessions[data["session"]].resume()
            if data["action"] == "quit":
                Hashcat.sessions[data["session"]].quit()

            res = {"response": "ok"}

            return json.dumps(res)
        except Exception as e:
            traceback.print_exc()

            return json.dumps({
                "response": "error",
                "message": str(e),
            })

    """
        Upload a new rule file
        Parameters are:
            - name: rule file name
            - rules: content of the file
    """
    def _upload_rule(self):
        try:
            data = json.loads(request.data.decode())

            Hashcat.upload_rule(data["name"], data["rules"])

            res = {"response": "ok"}

            return json.dumps(res)
        except Exception as e:
            traceback.print_exc()

            return json.dumps({
                "response": "error",
                "message": str(e),
            })

    """
        Upload a new mask file
        Parameters are:
            - name: mask file name
            - masks: content of the file
    """
    def _upload_mask(self):
        try:
            data = json.loads(request.data.decode())

            Hashcat.upload_mask(data["name"], data["masks"])

            res = {"response": "ok"}

            return json.dumps(res)
        except Exception as e:
            traceback.print_exc()

            return json.dumps({
                "response": "error",
                "message": str(e),
            })

    """
        Upload a new wordlist file
        Parameters are:
            - name: wordlist file name
            - wordlists: content of the file
    """
    def _upload_wordlist(self):
        try:
            data = json.loads(request.data.decode())

            Hashcat.upload_wordlist(data["name"], data["wordlists"])

            res = {"response": "ok"}

            return json.dumps(res)
        except Exception as e:
            traceback.print_exc()

            return json.dumps({
                "response": "error",
                "message": str(e),
            })





