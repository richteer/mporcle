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
# TODO: don't squash punctuation in plaintext representation
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
		# TODO: emit('yes word bc', {"index": i, "player": "SOMETHING"}, broadcast=True)
	else:
		emit('no word', {"index":i});

if __name__ == '__main__':
	sio.run(app)


TEMPSONG = '''Somebody once told me the world is gonna roll me I ain't the sharpest tool in the shed
She was looking kind of dumb with her finger and her thumb
In the shape of an L on her forehead
Well the years start coming and they don't stop coming
Fed to the rules and I hit the ground running
Didn't make sense not to live for fun
Your brain gets smart but your head gets dumb
So much to do, so much to see
So what's wrong with taking the back streets?
You'll never know if you don't go
You'll never shine if you don't glow
Hey now, you're an all-star, get your game on, go play
Hey now, you're a rock star, get the show on, get paid
And all that glitters is gold
Only shooting stars break the mold
It's a cool place and they say it gets colder
You're bundled up now, wait till you get older
But the meteor men beg to differ
Judging by the hole in the satellite picture
The ice we skate is getting pretty thin
The water's getting warm so you might as well swim
My world's on fire, how about yours?
That's the way I like it and I never get bored
Hey now, you're an all-star, get your game on, go play
Hey now, you're a rock star, get the show on, get paid
All that glitters is gold
Only shooting stars break the mold
Hey now, you're an all-star, get your game on, go play
Hey now, you're a rock star, get the show, on get paid
And all that glitters is gold
Only shooting stars
Somebody once asked could I spare some change for gas?
I need to get myself away from this place
I said yep what a concept
I could use a little fuel myself
And we could all use a little change
Well, the years start coming and they don't stop coming
Fed to the rules and I hit the ground running
Didn't make sense not to live for fun
Your brain gets smart but your head gets dumb
So much to do, so much to see
So what's wrong with taking the back streets?
You'll never know if you don't go
You'll never shine if you don't glow
Hey now, you're an all-star, get your game on, go play
Hey now, you're a rock star, get the show on, get paid
And all that glitters is gold
Only shooting stars break the mold
And all that glitters is gold
Only shooting stars break the mold'''

songs = {"foo" : gen_song()}
