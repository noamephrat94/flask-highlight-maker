from flask.helpers import flash
from sqlalchemy.sql.functions import user
from website.models import Note
import threading
from basketball_reference_scraper.box_scores import get_box_scores
import dailymotion
import moviepy.editor as mpe
from flask import Blueprint, render_template, flash, jsonify
from flask_login import login_required, current_user
import pytesseract
import cv2
import re
import ffmpeg
from pydub import AudioSegment
from pydub.utils import make_chunks
from moviepy.editor import *
from datetime import datetime
from basketball_reference_scraper.pbp import get_pbp
import pafy
import random
from .models import Videos
from . import db
from flask.globals import request
from .models import Note
import json
from .teams import teams_dict
import requests
from bs4 import BeautifulSoup
import datetime as dt
from .video_processing import *


views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    articles = latest_news()
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_PATH = os.path.join(ROOT_DIR, 'static')
    videos = os.listdir(os.path.join(CONFIG_PATH, "videos"))

    if request.method == 'POST':
        note = request.form.get('note')
        if len(note) < 1:
            flash('Note too short', category='error')
        else:
            new_note = Note(data=note, user_id=current_user.id)
            db.session.add(new_note)
            db.session.commit()
            flash('Note added!', category='success')

    scores = daily_scores()

    return render_template("home.html", articles=articles, videos=videos, scores=scores, user=current_user)


@views.route('/highlight', methods=['GET', 'POST'])
@login_required
def highlight():
    if request.method == 'POST':
        team1 = request.form.get('team1')
        team2 = request.form.get('team2')
        game_date = request.form.get('date')
        url = request.form.get('url')
        if len(team1) < 1:
            flash('team must be 3 characters.', category='error')
        elif len(team2) < 1:
            flash('team must be 3 characters.', category='error')
        # elif datetime.strptime(game_date, '%y/%m/%d') > datetime.now():
        #     flash('Must be passed date.', category='error')
        # elif "youtube" not in url or "youtu.be" not in url:
        #     flash('Must be a youtube url', category='error')
        elif len(url) < 5:
            flash('URL must be greater than 3 characters', category='error')
        else:
            print(teams_dict[team1], teams_dict[team2], game_date, url)
            res = get_input_data(teams_dict[team1], teams_dict[team2], url, game_date)
            team1=""
            team2=""
            game_date=""
            url=""
    scores = daily_scores()
    return render_template("highlight.html", scores=scores, teams=teams_dict, user=current_user)


@views.route('/delete-note', methods=['POST'])
def delete_note():
    note = json.loads(request.data)
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:
            db.session.delete(note)
            db.session.commit()

    return jsonify({})


@views.route('/delete-video', methods=['POST'])
def delete_video():
    video = json.loads(request.data)
    videoId = video['videoId']
    vid = Videos.query.get(videoId)
    if vid:
        print("Hello")
        print(vid)
        if vid.user_id == current_user.id:
            db.session.delete(vid)
            db.session.commit()

    return jsonify({})


@views.route('/gallery')
def gallery():
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_PATH = os.path.join(ROOT_DIR, 'static')
    videos = os.listdir(os.path.join(CONFIG_PATH, "videos"))
    scores = daily_scores()
    return render_template('gallery.html', scores=scores, videos=videos, user=current_user, vids=Videos)

@views.route('/shotplot')
def shotplot():
    scores = daily_scores()
    return render_template('shotplot.html', scores=scores, user=current_user)


def daily_scores():
    d = dt.date.today()
    x = d - dt.timedelta(days=1)
    year = x.year
    month = f"{x.month:02d}"
    day = f"{x.day:02d}"
    jsn = f"https://data.nba.net/10s/prod/v1/{year}{month}{day}/scoreboard.json"
    # jsn = f"https://data.nba.net/10s/prod/v1/20200122/scoreboard.json"
    page = requests.get(jsn)
    y = json.loads(page.content)

    scores = []
    for game in range(len(y['games'])):
        scores.append((y['games'][game]['vTeam']['triCode'], y['games'][game]['vTeam']['score'], \
             y['games'][game]['hTeam']['triCode'], y['games'][game]['hTeam']['score']))
    return scores


def latest_news():
    URL = "https://www.espn.com/nba/"
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    results = soup.find_all("div", class_="headlineStack")
    articles = []
    for res in range(len(results)):
        for link in results[res].findAll('a'):
            text = link.findAll(text=True)
            articles.append((text[0], "https://www.espn.com/nba" + link.get('href')))
        return articles


# This one worked before the code was moved to video_processing.py

# @views.route('/gallery', methods=['GET', 'POST'])
# @login_required
# def get_input_data(team1, team2, url, date):
#     try:
#         global game_name
#         random_id = ''.join([str(random.randint(0, 999)).zfill(3) for _ in range(2)])
#         game_name = f'{date}_{team1}_{team2}_{random_id}'
#         df = get_pbp(date, team1, team2)
#         ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
#         CONFIG_PATH = os.path.join(ROOT_DIR, 'static')
#         df.to_csv(f'{CONFIG_PATH}/game_csvs/{game_name}.csv')
#         plays = dict()
#         game_action = [col for col in df.columns if 'ACTION' in col]
#         for index, row in df.iterrows():
#             if type(row[game_action[0]]) == str and 'make' in row[game_action[0]] and 'free' not in row[game_action[0]]:
#                 print(str(row['TIME_REMAINING']).split(".")[0], row[game_action[0]])
#                 plays.update({str(row['TIME_REMAINING']).split(".")[0]: [row[game_action[0]], row['QUARTER']]})
#             elif type(row[game_action[1]]) == str and 'make' in row[game_action[1]] and 'free' not in row[game_action[1]]:
#                 print(str(row['TIME_REMAINING']).split(".")[0], row[game_action[1]])
#                 plays.update({str(row['TIME_REMAINING']).split(".")[0]: [row[game_action[1]], row['QUARTER']]})
#
#         vPafy = pafy.new(url)
#         best = vPafy.getbest(preftype="mp4")
#
#         cap = cv2.VideoCapture(best.url)
#         # cap = cv2.VideoCapture(game_film)
#         video = VideoFileClip(best.url)
#         frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
#         fps = cap.get(cv2.CAP_PROP_FPS)
#         duration = frame_count / fps
#         print(fps)
#         out = cv2.VideoWriter('test_new_short.mp4', cv2.VideoWriter_fourcc(*'mp4v'), fps, (1280, 720))
#         ret, frame = cap.read()
#         frame_loc = []
#         count = 0
#         image_array = []
#         start = datetime.now()
#         while cap.isOpened():
#             prev_frame = frame[:]
#             ret, frame = cap.read()
#             try:
#                 if ret:
#                     crop_img = frame[520:720, 0:1280]
#                     crop_img = cv2.resize(crop_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
#
#                     gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
#                     thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
#                     blurred = cv2.GaussianBlur(thresh, (5, 5), 0)
#                     flipped = (255 - blurred)
#                     # cv2.imwrite('/Users/noame/Downloads/Archive2/captions/{}.jpg'.format(count), blurred)
#                     cv2.imwrite('/Users/noame/Downloads/Archive2/captions/{}.jpg'.format(count), flipped)
#
#                     # Pytesseract OCR multiple config options: https://newbedev.com/pytesseract-ocr-multiple-config-options
#
#                     data = pytesseract.image_to_string(blurred, lang='eng', config='--psm 11')
#                     data += pytesseract.image_to_string(flipped, lang='eng', config='--psm 11')
#                     data = data.lower()
#                     qtr = None
#                     if "2nd" in data or "2n" in data or "znd" in data:
#                         qtr = 2
#                     elif "3rd" in data or "3r" in data or "3r0" in data or "3ro" in data or "37d" in data or "3fd" in \
#                             data or "31d" in data:
#                         qtr = 3
#                     elif "4th" in data or "4t" in data or "47h" in data or '41h' in data or '4h' in data:
#                         qtr = 4
#                     # elif "ot" in data:
#                     #     qtr = '1OT'
#                     elif "1st" in data or "ist" in data or "ast" in data:
#                         qtr = 1
#                     else:
#                         qtr = None
#
#                     x = re.findall(r'\d+:\d\d', data)
#                     if x:
#                         if str(x).split("'")[1] in plays.keys() and qtr == plays[str(x).split("'")[1]][1]:
#                             cv2.imwrite('/Users/noame/Downloads/Archive2/captions/{}.jpg'.format(plays[str(x).split("'")[1]][0]),prev_frame)
#
#                             curr_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
#
#                             ret, frame = cap.read()
#                             frame_loc.append(curr_frame)
#                             # # Try in one loop
#                             # cap.set(cv2.CAP_PROP_POS_FRAMES, curr_frame - fps*4)
#                             # ret, frame = cap.read()
#                             # while curr_frame - cap.get(cv2.CAP_PROP_POS_FRAMES) <= fps*4 and cap.get(cv2.CAP_PROP_POS_FRAMES) - curr_frame <= fps*4:
#                             #     out.write(frame)
#                             #     cap.set(1, cap.get(cv2.CAP_PROP_POS_FRAMES) + 1)
#                             #     ret, frame = cap.read()
#
#                             print(frame_loc)
#                             print("QTR:", qtr, "time:", str(x).split("'")[1], plays[str(x).split("'")[1]][0])
#                             del plays[str(x).split("'")[1]]
#
#                     count += fps  # i.e. at 30 fps, this advances one second
#                     cap.set(1, count)
#                     if cap.get(cv2.CAP_PROP_POS_FRAMES) >= frame_count:
#                         cap.release()
#                         break
#                 else:
#                     cap.release()
#                     break
#             except Exception as e:
#                 print(e)
#         out.release()
#         cap.release()
#         end_part_one = datetime.time
#         print("First Iteration took: {}".format(datetime.now() - start))
#         print(frame_loc)
#         print("Finished relevant frame search")
#         # audio = video.audio.write_audiofile('/Users/noame/downloads/game_audio.wav')
#         # audio = AudioSegment.from_file('/Users/noame/downloads/game_audio.wav', "wav")
#         #Saving chunks
#         # chunk_length_ms = 1000 # pydub calculates in millisec
#         # chunks = make_chunks(audio, chunk_length_ms) #Make chunks of one sec
#         # combined = AudioSegment.empty()
#
#         #Crop relevant audio segments
#         # for f in frame_loc:
#         #     i = round((f-fps*4)/fps)
#         #     while i <= round((f+fps*4)/fps)-2:
#         #         combined += chunks[i]
#         #         i += 1
#         #
#         # combined.export("/Users/noame/downloads/new_test_output.wav", format="wav")
#         # print("Finished audio cropping")
#         # input_video = ffmpeg.input('test_new_short.mp4')
#         # input_audio = ffmpeg.input('/Users/noame/downloads/new_test_output.wav')
#         # output_path = f'/Users/noame/downloads/{game_name}.mp4'
#         ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
#         CONFIG_PATH = os.path.join(ROOT_DIR, 'static')
#         videos = os.path.join(CONFIG_PATH, "videos")
#         output_path = f'{videos}/{game_name}.mp4'
#         clips = []
#         for frame in frame_loc:
#             if round(frame / fps) < 4:
#                 clip_name = video.subclip(round(frame / fps), round(frame / fps) + 2)
#             elif round(frame / fps) + 4 >= video.duration:
#                 clip_name = video.subclip(round(frame / fps) - 4, round(frame / fps))
#             else:
#                 clip_name = video.subclip(round(frame / fps) - 4, round(frame / fps) + 2)
#             clips.append(clip_name)
#         print(clips)
#         final_clip = concatenate_videoclips(clips)
#         final_clip.write_videofile(output_path,
#                                    codec='libx264',
#                                    audio_codec='aac')
#         print("Finished Highlight Creation!")
#         print(f"Recall: {len(frame_loc)/len(plays)}")
#         # final = ffmpeg.concat(input_video, input_audio, v=1, a=1).output(output_path).run()
#
#         new_video = Videos(game_name=game_name, user_id=current_user.id, id=random_id)
#         db.session.add(new_video)
#         db.session.commit()
#
#         return render_template('gallery.html', videos=videos, user=current_user)
#     except Exception as e:
#         print(e)
#         print("Failed!")
#         flash('Error, Please Try Again!', category='error')
#         return render_template('highlight.html', user=current_user)



# def get_input_data(team1, team2, url, date):
#     global game_name
#     game_name = f'{date}_{team1}_{team2}'
#     plays, game_name = get_game_data(date, team1, team2)
#     cap, video = load_video(url)
#     create_video_highlights(plays, cap, video)
#
# def get_game_data(date, team1, team2):
#     # df = get_pbp('2010-04-20', 'LAL', 'GSW')
#     flash("Don't touch anything while this message is shown", category='error')
#     try:
#         df = get_pbp(date, team1, team2)
#         df.to_csv(f'{game_name}.csv')
#         plays = dict()
#         game_action = [col for col in df.columns if 'ACTION' in col]
#         for index, row in df.iterrows():
#             if type(row[game_action[0]]) == str and 'make' in row[game_action[0]] and 'free' not in row[game_action[0]]:
#                 print(str(row['TIME_REMAINING']).split(".")[0], row[game_action[0]])
#                 plays.update({str(row['TIME_REMAINING']).split(".")[0]: [row[game_action[0]], row['QUARTER']]})
#             elif type(row[game_action[1]]) == str and 'make' in row[game_action[1]] and 'free' not in row[game_action[1]]:
#                 print(str(row['TIME_REMAINING']).split(".")[0], row[game_action[1]])
#                 plays.update({str(row['TIME_REMAINING']).split(".")[0]: [row[game_action[1]], row['QUARTER']]})
#     except Exception as e:
#         print(e)
#         flash("Something wrong with the input data (teams or date are incorrect) please try again")
#         return None
#     return plays, game_name
#
#
# def load_video(game_url):
#     #local video on machine
#     game_film = '/Users/noame/Downloads/Los Angeles Lakers vs Milwaukee Bucks Full Game Highlights _ 2020-21 NBA Season.mp4'
#
#     #read directly from youtube
#     # url = 'https://www.youtube.com/watch?v=T2zH3GTSTqc'
#     url = game_url
#     vPafy = pafy.new(url)
#     best = vPafy.getbest(preftype="mp4")
#
#     cap = cv2.VideoCapture(best.url)
#     # cap = cv2.VideoCapture(game_film)
#     video = VideoFileClip(best.url)
#     return cap, video
#
# # check that the quarter
# def check_quarter(blurred):
#     data = pytesseract.image_to_string(blurred, lang='eng', config='--psm 6')
#     data = data.lower()
#     qtr = None
#     if "st" in data:
#         qtr = 1
#     elif "nd" in data or "2n" in data or "znd" in data:
#         qtr = 2
#     elif "rd" in data or "3r" in data or "3r0" in data or "3ro" in data:
#         qtr = 3
#     elif "th" in data or "4t" in data or "47h" in data or '41h' in data or '4h' in data:
#         qtr = 4
#     elif "ot" in data:
#         qtr = '1OT'
#     else:
#         qtr = None
#
#     return data, qtr
#
#
# def create_video_highlights(plays, cap, video):
#     out = cv2.VideoWriter('test_new_short.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 15, (1280, 720))
#     ret, frame = cap.read()
#     frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     duration = frame_count / fps
#     print(fps)
#     frame_loc = []
#     count = 0
#     image_array = []
#     start = datetime.now()
#     while cap.isOpened():
#         prev_frame = frame[:]
#         ret, frame = cap.read()
#         try:
#             if ret:
#                 crop_img = frame[520:720, 0:1280]
#                 crop_img = cv2.resize(crop_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
#
#                 gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
#                 thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
#                 blurred = cv2.GaussianBlur(thresh, (5, 5), 0)
#
#                 cv2.imwrite('/Users/noame/Downloads/Archive2/captions/{}.jpg'.format(count), blurred)
#                 data, qtr = check_quarter(blurred)
#
#                 x = re.findall(r'\d+:\d\d', data)
#                 if x:
#                     if str(x).split("'")[1] in plays.keys() and qtr == plays[str(x).split("'")[1]][1]:
#                         cv2.imwrite('/Users/noame/Downloads/Archive2/captions/{}.jpg'.format(plays[str(x).split("'")[1]][0]),prev_frame)
#
#                         curr_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
#
#                         ret, frame = cap.read()
#                         frame_loc.append(curr_frame)
#                         # # Try in one loop
#                         cap.set(cv2.CAP_PROP_POS_FRAMES, curr_frame - 30*4)
#                         ret, frame = cap.read()
#                         while curr_frame - cap.get(cv2.CAP_PROP_POS_FRAMES) <= 30*4 and cap.get(cv2.CAP_PROP_POS_FRAMES) - curr_frame <= 30*2:
#                             out.write(frame)
#                             cap.set(1, cap.get(cv2.CAP_PROP_POS_FRAMES) + 1)
#                             ret, frame = cap.read()
#
#                         print(frame_loc)
#                         print("QTR:", qtr, "time:", str(x).split("'")[1], plays[str(x).split("'")[1]][0])
#                         del plays[str(x).split("'")[1]]
#
#                 count += 30 # i.e. at 30 fps, this advances one second
#                 cap.set(1, count)
#                 if cap.get(cv2.CAP_PROP_POS_FRAMES) >= frame_count:
#                     cap.release()
#                     break
#             else:
#                 cap.release()
#                 break
#         except Exception as e:
#             print(e)
#     out.release()
#     cap.release()
#     end_part_one = datetime.time
#     print("First Iteration took: {}".format(datetime.now() - start))
#     print(frame_loc)
#     print("Finished relevant frame search")
#     crop_audio(video, frame_loc)
#
#
# # Crop the audio
# def crop_audio(video, frame_loc):
#     audio = video.audio.write_audiofile('/Users/noame/downloads/game_audio.wav')
#     audio = AudioSegment.from_file('/Users/noame/downloads/game_audio.wav', "wav")
#     #Saving chunks
#     chunk_length_ms = 1000 # pydub calculates in millisec
#     chunks = make_chunks(audio, chunk_length_ms) #Make chunks of one sec
#     combined = AudioSegment.empty()
#
#     #Crop relevant audio segments
#     for f in frame_loc:
#         i = round((f-30*4)/30)
#         while i <= round((f+30*2)/30)-2:
#             combined += chunks[i]
#             i += 1
#     combined.export("/Users/noame/downloads/new_test_output.wav", format="wav")
#     print("Finished audio cropping")
#     export_final_video()
#
#
# # Save the final video to the local machine and upload it to dailymotion
# def export_final_video():
#     input_video = ffmpeg.input('test_new_short.mp4')
#     input_audio = ffmpeg.input('/Users/noame/downloads/new_test_output.wav')
#     output_path = f'/Users/noame/downloads/{game_name}.mp4'
#     ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
#     CONFIG_PATH = os.path.join(ROOT_DIR, 'static')
#     videos = os.listdir(os.path.join(CONFIG_PATH, "videos"))
#     output_path = f'{videos}/{game_name}.mp4'
#     final = ffmpeg.concat(input_video, input_audio, v=1, a=1).output(output_path).run()
#
#     API_KEY = 'bd5a4c9da2e64c5fdf95'
#     API_SECRET = 'd3446a1ad612af2b2362a5cafbdf81462a94818e'
#     USERNAME = 'noamephrat94@gmail.com'
#     PASSWORD = 'Brooklyn2434!'
#     USER_ID = 'x2hsu3z'
#
#     try:
#         d = dailymotion.Dailymotion()
#         d.set_grant_type('password', api_key=API_KEY, api_secret=API_SECRET,
#             scope=['manage_videos'], info={'username': USERNAME, 'password': PASSWORD})
#         url = d.upload(output_path)
#         d.post('/me/videos',
#             {f'url': url, 'title': {game_name}, 'published': 'true', 'channel': 'news'})
#         print("Video uploaded to dailymotion successfully")
#     except Exception as e:
#         print("Error video was not uploaded: {}".format(e))


