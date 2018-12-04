from flask import Flask, render_template, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
sio = SocketIO(app, logger=True)

def hash_djb2(s):
	hash = 5381
	for x in s:
		hash = (( hash << 5) + hash) + ord(x)
	return hash & 0xFFFFFFFF

# TODO: make this take arbitrary lyric data, maybe a salt
def gen_song():
	ls = TEMPSONG.replace("\n", " ").lower()
	ls = re.sub('[^a-zA-Z ]', '', ls)
	ls = ls.split(" ")
	return ls

@app.route('/')
def index():
	"""Serve the client-side application."""
	return send_from_directory('.', 'index.html')

@app.route('/song')
def get_song():
	return jsonify(list(map(hash_djb2, songs["foo"])))

def get_song2():
	ls = TEMPSONG.replace("\n", " ").lower()
	ls = re.sub('[^a-zA-Z ]', '', ls)
	ls = ls.split(" ")

	ls = list(map(hash_djb2, ls))
	return jsonify(ls)


@sio.on('connect', namespace='/chat')
def connect(sid, environ):
	print("connect ", sid)

@sio.on('chat message', namespace='/chat')
def message(sid, data):
	print("message ", data)
	sio.emit('reply', room=sid)

@sio.on('disconnect', namespace='/chat')
def disconnect(sid):
	print('disconnect ', sid)


@sio.on('try word')
def tryword(data):
	i = data["index"]
	word = songs["foo"][i]

	if word == data["word"]:
		emit('yes word', {"index":i, "plain": word})
	else:
		emit('no word', {"index":i});

if __name__ == '__main__':
	sio.run(app)


TEMPSONG = '''insert test song here'''

songs = {"foo" : gen_song()}
