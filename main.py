from flask import Flask, render_template, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import re

class GameMode():
	def init(self):
		pass
	def __init__(self, state):
		self.state = state # in case the mode needs state access
		self.init()
	def start_game(self):
		pass
	def tryword(self, data):
		pass

class MatchAnywhereMode(GameMode):
	def tryword(self, data):
		i = data["index"]
		word = songs["foo"][i]  # TODO be self-referential for what game data is selected

		if word == data["word"]:
			data["plain"] = word # TODO: conver to real plaintext here
			return (True, data, data)
		return (False, data, None)

class SequenceMode(GameMode):
	def init(self):
		self.current_index = 0

	def start_game(self):
		self.current_index = 0

	def tryword(self, data):
		word = songs["foo"][self.current_index]  # TODO be self-referential

		if word == data["word"]:
			self.current_index += 1
			data["plain"] = word
			data["next_index"] = self.current_index
			return (True, data, data)

		data["next_index"] = self.current_index
		return (False, data, None)


class State():
	def __init__(self):
		self.users = []
		self.ready = []
		self.running = False
		self.set_mode("match")
		self.tryword_check = None

	# Convert a game data blob into a useful form for managing state
	def prepare_data(self, blob):
		pass

	def start_game(self):
		self.running = True
		self.ready = []
		self.mode.start_game()

	def stop_game(self):
		self.running = False
		self.ready = []
		#self.mode.stop_game() # TODO

	# Add/remove user from the ready list, and return the new status
	def toggle_ready_user(self, user):
		if user in self.ready:
			self.ready.remove(user)
			return False
		else:
			self.ready.append(user)
			return True

	# Expects "word", "index" to be filled, and returns a triple of
	#  Boolean - was the word correct or not
	#  Dict - data to pass to the sender
	#  Dict - data to broadcast to everyone
	# self.tryword_check is to be set to the current game mode's handler
	# TODO: Acutally define those exceptions for proper catching
	def tryword(self, data):
		if not self.running:
			raise Exception("Tryword called without game started")

		if not self.mode:
			raise Exception("Mode never set")

		return self.mode.tryword(data)


	# Set the mode flag and and game handlers
	def set_mode(self, mode):
		if mode == "match":
			self.mode = MatchAnywhereMode(self)
		elif mode == "sequence":
			self.mode = SequenceMode(self)
		else:
			return False # Bad mode switch sent by client
		return True

games = {}

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


@sio.on('disconnect')
def disconnect():
	id = request.sid
	ls = [i for i in rooms() if i != id]
	for l in ls:
		# Explicitly call the cleanup
		emit("user leave", {"room": l, "id": id}, room=l)
		user_leave(id, l)

# Helper function to clean up game states
def user_leave(user, gid):
	print("removing {} from {}".format(user, gid))
	state = games.get(gid)
	if not state:
		print("Game id {} not found".format(gid))
		return

	print(state.users)
	try:
		state.users.remove(user)
	except Exception as e:
		print(e)

	# If this is the last user to leave, destroy this game context
	if not state.users:
		print("deleting game state: " + gid)
		del games[gid]


@sio.on('connect')
def connect():
	pass

@sio.on('join')
def join(data):
	user = request.sid
	gid = data['room']
	state = games.get(gid)

	# Game state not found, lets create one
	if not state:
		print("creating new game state: " + gid)
		state = State()
		games[gid] = state

	state.users.append(user)

	join_room(gid)
	emit("join success", {"room": gid})
	emit("user join", {"room": gid, "id": user}, room=gid, include_self=False)

@sio.on('ready')
def ready(data):
	uid = request.sid
	state = games.get(data['room'])
	# TODO: check that a player isn't trying to start a game in a room they are not in?
	if not state:
		return # TODO: error message?

	ret = state.toggle_ready_user(uid)
	emit('user ready', {"user": uid, "state": ret}, room=data['room'], include_self=False)

	if len(state.ready) == len(state.users):
		emit('game start', broadcast=True, room=data['room'])
		state.running = True

@sio.on('surrender')
def surrender(data):
	gid = data.get("room")

	ret = game_end(gid)

	emit('game stop', ret, broadcast=True, room=gid)

# Helper for all the close game reset logic
def game_end(gid):
	state = games.get(gid)
	state.stop_game()

	state.ready = []

	data = {}
	return data

@sio.on("mode change")
def mode_change(data):
	gid = data.get("room")
	if not gid:
		print("room not set in data")
		return
	state = games.get(gid)
	if not state:
		print("state not found for room: " + gid)
		return

	if state.set_mode(data.get("mode")):
		emit("mode change", data, room=gid, broadcast=True)


@sio.on('try word')
def tryword(data):
	state = games.get(data["room"])
	if not state:
		print("COULD NOT FIND GAME: " + data["room"])
		return

	success, resp, respBC = state.tryword(data)

	if success:
		emit('yes word', resp) # tell them they are correct
		emit('yes word bc', respBC, room=data["room"], broadcast=True)
	else:
		emit('no word', resp, room=data["room"]);

if __name__ == '__main__':
	sio.run(app)

@sio.on('chat')
def chat(data):
	print(request.sid)
	gid = data["room"]
	data["user"] = request.sid
	emit('chat', data, room=gid, broadcast=True)


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
