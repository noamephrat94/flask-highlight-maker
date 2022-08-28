from flask import Blueprint, render_template, flash, jsonify
from flask_login import login_required, current_user
import pytesseract
from PIL import Image
import cv2
from moviepy.editor import *
from datetime import datetime
import random
from .models import Videos
from . import db
from .pbp_data import *
import os
import numpy as np
# import ray
import time
# import easyocr
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
from basketball_reference_scraper.pbp import get_pbp
import pafy
import re
# import tesserocr


# this needs to run only once to load the model into memory
# reader = easyocr.Reader(['en'])

views = Blueprint('views', __name__)

@views.route('/gallery', methods=['GET', 'POST'])
@login_required
def get_input_data(team1, team2, url, date):
	try:
		plays, game_name, random_id = get_pbp_data(date, team1, team2)
		# print(plays, game_name, random_id)
		cap, video, frame_count, fps = prep_orig_vid(url)
		frame_loc = process_game_film(cap, plays, frame_count, fps)
		create_video(frame_loc, fps, video, game_name)
		commit_video_to_db(game_name, random_id)

		return render_template('gallery.html', user=current_user)
	except Exception as e:
		print(e)
		print("Failed!")
		flash('Error, Please Try Again!', category='error')
		return render_template('highlight.html', user=current_user)


def get_pbp_data(date, team1, team2):
	print("Getting pbp data")
	random_id = ''.join([str(random.randint(0, 999)).zfill(3) for _ in range(2)])
	game_name = f'{date}_{team1}_{team2}_{random_id}'
	# df = get_pbp(date, team1, team2)
	ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
	CONFIG_PATH = os.path.join(ROOT_DIR, 'static')
	# df.to_csv(f'{CONFIG_PATH}/game_csvs/{game_name}.csv')
	# print(df['QUARTER'].unique())
	plays = distribute(team1, team2, date)
	# plays = dict()
	# game_action = [col for col in df.columns if 'ACTION' in col]
	# for index, row in df.iterrows():
	# 	if type(row[game_action[0]]) == str and 'make' in row[game_action[0]] and 'free' not in row[
	# 		game_action[0]]:
	# 		print(str(row['TIME_REMAINING']).split(".")[0], row[game_action[0]])
	# 		plays.update({str(row['TIME_REMAINING']).split(".")[0]: [row[game_action[0]], row['QUARTER']]})
	# 	elif type(row[game_action[1]]) == str and 'make' in row[game_action[1]] and 'free' not in row[
	# 		game_action[1]]:
	# 		print(str(row['TIME_REMAINING']).split(".")[0], row[game_action[1]])
	# 		plays.update({str(row['TIME_REMAINING']).split(".")[0]: [row[game_action[1]], row['QUARTER']]})
	return plays, game_name, random_id


def prep_orig_vid(url):
	print("Prepping orig game film....")
	# vPafy = pafy.new(url)
	# best = vPafy.getbest(preftype="mp4")
	# best.download()
	# cap = cv2.VideoCapture(best.url)
	# video = VideoFileClip(best.url)
	cap = cv2.VideoCapture("/Users/noame/Downloads/Y2Mate.is - Boston Celtics vs Los Angeles Lakers 17.06.2010 - NBA Finals - game 7-KMxDbSWFjkk-720p-1640170955272.mp4")
	video = VideoFileClip("/Users/noame/Downloads/Y2Mate.is - Boston Celtics vs Los Angeles Lakers 17.06.2010 - NBA Finals - game 7-KMxDbSWFjkk-720p-1640170955272.mp4")
	# cap = cv2.VideoCapture("/Users/noame/Downloads/Golden State Warriors vs Toronto Raptors - Game 6 - June 13, Full 1st Qtr _ 2019 NBA Finals.mp4")
	# video = VideoFileClip("/Users/noame/Downloads/Golden State Warriors vs Toronto Raptors - Game 6 - June 13, Full 1st Qtr _ 2019 NBA Finals.mp4")
	frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
	fps = cap.get(cv2.CAP_PROP_FPS)
	duration = frame_count / fps
	print(f"fps: {fps}\nDuration: {duration}")
	return cap, video, frame_count, fps


def create_video(frame_loc, fps, video, game_name):
	print("Creating the video from frames found.....")
	ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
	CONFIG_PATH = os.path.join(ROOT_DIR, 'static')
	videos = os.path.join(CONFIG_PATH, "videos")
	output_path = f'{videos}/{game_name}.mp4'
	clips = []
	for frame in frame_loc:
		if round(frame / fps) < 4:
			clip_name = video.subclip(round(frame / fps), round(frame / fps) + 2)
		elif round(frame / fps) + 4 >= video.duration:
			clip_name = video.subclip(round(frame / fps) - 4, round(frame / fps))
		else:
			clip_name = video.subclip(round(frame / fps) - 4, round(frame / fps) + 2)
		clips.append(clip_name)
	print(clips)
	final_clip = concatenate_videoclips(clips)
	final_clip.write_videofile(output_path,
	                           codec='libx264',
	                           audio_codec='aac',
	                           fps=fps)
	print("Finished Highlight Creation!")
	# print(f"Recall: {len(frame_loc) / len(plays)}")



def commit_video_to_db(game_name, random_id):
	print("Commiting video to db....")
	try:
		new_video = Videos(game_name=game_name, user_id=current_user.id, id=random_id)
		db.session.add(new_video)
		db.session.commit()
		print("Uploaded to db successfully!!")
	except Exception as e:
		print("Error uploading video to db", e)


def process_game_film(cap, plays, frame_count, fps):
	print("Proccesing the game film.....")
	ret, frame = cap.read()
	frame_loc = []
	count = 0
	start = datetime.now()
	while cap.isOpened():
		prev_frame = frame[:]
		ret, frame = cap.read()
		try:
			if ret:
				# mp_handler(cap, frame, plays, prev_frame, frame_loc) 
				crop_img = frame[520:720, 0:1280]
				crop_img = cv2.resize(crop_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
				
				gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
				thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
				blurred = cv2.GaussianBlur(thresh, (5, 5), 0)
				flipped = (255 - blurred)
				
				# Pytesseract OCR multiple config options: https://newbedev.com/pytesseract-ocr-multiple-config-options
				data = pytesseract.image_to_string(blurred, lang='eng', config='--psm 11')
				data += pytesseract.image_to_string(flipped, lang='eng', config='--psm 11')
				tess = Image.fromarray(np.uint8(blurred)).convert('RGB')
				tess2 = Image.fromarray(np.uint8(flipped)).convert('RGB')
				data += tesserocr.image_to_text(tess)
				data += tesserocr.image_to_text(tess2)

				# result = reader.readtext(crop_img)
				# extracted = ''
				# for res in result:
				# 	extracted += " " + res[1]
				# print(extracted)
				# data += extracted
				data = data.lower()
				# print(data.replace("\n", ""))
				x, y, z = '', '', ''
				x = re.findall(r'\d+:\d\d', data)
				y = re.findall(r'\:\d\d', data)
				z = re.findall(r'\d\d.\d', data)
				qtr = None
				if "2nd" in data or "2n" in data or "znd" in data:
					qtr = 2
				elif "3rd" in data or "3r" in data or "3r0" in data or "3ro" in data or "37d" in data or "3fd" in \
						data or "31d" in data:
					qtr = 3
				elif "4th" in data or "4t" in data or "47h" in data or '41h' in data or '4h' in data:
					qtr = 4
				elif "ot" in data or "0t" in data:
				    qtr = '1OT'
				elif "1st" in data or "ist" in data or "ast" in data or "st" in data:
					qtr = 1
				else:
					qtr = None

				if x:
					if x[0] in plays.keys() and qtr == plays[x[0]][1]:
						# cv2.imwrite('/Users/noame/Downloads/Archive2/captions/{}.jpg'.format(
						# 	plays[str(x).split("'")[1]][0]), prev_frame)
						curr_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
						frame_loc.append(curr_frame)
						print(frame_loc)
						print("QTR:", qtr, "time:", x[0], plays[x[0]][0])
						del plays[x[0]]

				elif y:
					if y[0] in plays.keys() and qtr == plays[y[0]][1]:
						curr_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
						frame_loc.append(curr_frame)
						print(frame_loc)
						print("QTR:", qtr, "time:", y[0], plays[y[0]][0])
						del plays[y[0]]

				elif z:
					if z[0].split(".")[0] in plays.keys() and qtr == plays[z[0].split(".")[0]][1]:
						curr_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
						frame_loc.append(curr_frame)
						print(frame_loc)
						print("QTR:", qtr, "time:", z[0].split(".")[0], plays[z[0].split(".")[0]][0])
						del plays[z[0].split(".")[0]]
						# count += fps*3

				count += fps  # i.e. at 30 fps, this advances one second
				cap.set(1, count)
				if cap.get(cv2.CAP_PROP_POS_FRAMES) >= frame_count:
					cap.release()
					break
			else:
				cap.release()
				break
		except Exception as e:
			print(e)
	cap.release()
	end_part_one = datetime.time
	print("First Iteration took: {}".format(datetime.now() - start))
	print(frame_loc)
	print("Finished relevant frame search!!")
	return frame_loc




