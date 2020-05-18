import os 
import sys
import requests 
import traceback
import os.path

from bs4 import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

class WorkerSignals(QObject):

	start = pyqtSignal()
	finished = pyqtSignal()
	error = pyqtSignal(tuple)
	result = pyqtSignal(object)
	progress = pyqtSignal(str, int, int)

class Worker(QRunnable):

	def __init__(self, fn, *args, **kwargs):

		super(Worker, self).__init__()

		# Store constructor arguments (re-used for processing)
		self.fn = fn
		self.args = args
		self.kwargs = kwargs
		self.signals = WorkerSignals()    

		# Add the callback to our kwargs
		self.kwargs['progress_callback'] = self.signals.progress     

	# Run the differents signals and their results
	@pyqtSlot()
	def run(self):

		try:
			self.signals.start.emit()
			result = self.fn(*self.args, **self.kwargs)
		except:
			traceback.print_exc()
			exctype, value = sys.exc_info()[:2]
			self.signals.error.emit((exctype, value, traceback.format_exc()))
		else:
			self.signals.result.emit(result)  
		finally:
			self.signals.finished.emit()  

class InstaScrap(QWidget):

	def __init__(self):
		super().__init__()

		self.initUI()

	def initUI(self):

		# Set the root path
		self.path = os.getcwd()

		# Set validators
		onlyInt = QIntValidator()
		regex=QRegExp("[a-z-A-Z-1-9_]+")
		validator = QRegExpValidator(regex)

		# Set the labels 
		label_input = QLabel()
		label_number = QLabel()
		self.label_indicator = QLabel()
		label_input.setText("Enter an # : ")
		label_number.setText("Number of image to scrap")
		self.label_indicator.setAlignment(Qt.AlignCenter)

		# Set the input field
		self.input_search = QLineEdit(self)
		self.input_numbers = QLineEdit(self)
		self.input_search.setValidator(validator)
		self.input_numbers.setValidator(onlyInt)
		self.input_numbers.setText("50")

		# Set the progress bar
		self.bar_progress = QProgressBar(self)
		self.bar_progress.setVisible(False)

		# Set the buton
		self.btn_scrap = QPushButton("Scrap !")

		# Set the threadpool
		self.threadpool = QThreadPool()
		self.threadpool.setMaxThreadCount(5)

		# Set search box 
		box_search = QVBoxLayout()
		box_search.addWidget(label_input)
		box_search.addWidget(self.input_search)
		box_search.addWidget(label_number)
		box_search.addWidget(self.input_numbers)

		# set the input box
		box_input = QHBoxLayout()
		box_input.addLayout(box_search)
		
		# Set the progress box
		box_progress = QHBoxLayout()
		box_progress.addWidget(self.label_indicator)
		box_progress.addWidget(self.bar_progress)
		box_progress.setAlignment(Qt.AlignLeft)

		# Set the button box
		box_btn = QHBoxLayout()
		box_btn.addWidget(self.btn_scrap)
		box_btn.setAlignment(Qt.AlignLeft)
		
		# Set the bottombox 
		box_bottom = QHBoxLayout()
		box_bottom.addLayout(box_btn)
		box_bottom.addLayout(box_progress)
		
		# Set boxes layout
		box_main = QVBoxLayout()
		box_main.addLayout(box_input)
		box_main.addLayout(box_bottom)

		# Setting the main windows
		self.setLayout(box_main)
		self.setGeometry(300, 300,450, 50)
		self.setWindowTitle('InstaScrap')
		self.setWindowIcon(QIcon('web.png'))        
		self.show()

		# Connect button to the launcher
		self.btn_scrap.clicked.connect(self.launcher)
		
	# Scrapper function
	def scrapper(self, progress_callback):

		# get the requests
		request =  self.input_search.text()
		number_pictures = int(self.input_numbers.text())

		# Set condition to not run an infinite loop
		if len(request) >= 1 and number_pictures != 0 :

			# Set the function variable
			results =[]
			images = []
			videos = []
			nextpage = []
			counter_progress = 0
			counter_videos = 0
			url = "http://gramlook.com/hashtag/{}/".format(request)
			
			# Collect all the requested picture
			while len(results) < number_pictures :	

				counter_progress += 1

				progress_callback.emit("Colecting Urls ", 0, 0)

				# Set the soup 
				page = requests.get(url)
				soup = BeautifulSoup(page.content, 'html.parser')
				
				# Get all the images/videos pages
				for a in soup.find_all('a', attrs={"style": "position:relative;display:inline-block;"}) 
					results.append(a['href'])

				# If no results stop the function
				if len(results) < 1:
					self.label_indicator.setText("No Results")
					self.btn_scrap.setEnabled(True)
					break

				# Jump to the next page
				url = soup.find('a', href=True, attrs={"class": "ggbb"})["href"]

			counter_progress = 0

			# Adjust the page numbers to match the request	
			adjust = len(results) - number_pictures
			del results[-adjust:]
			
			# Scrap all the images with beautifulsoup
			for result in results:

				# Set the loop variables and the progressbar
				counter_progress += 1
				bar_length = len(results)
				progress_callback.emit("Fetching ", counter_progress, bar_length)

				# Set the soup 
				page = requests.get(result)
				soup = BeautifulSoup(page.content, 'html.parser')

				# Add the videos and the images to their respectives list
				try :
					images.append(soup.find('img', src=True, attrs={'class':'bi'})["src"])
				except :
					videos.append(soup.find("source").get("src"))

			# Reinit the counter for future loops
			counter_progress = 0

			# if there is images in the lists create the folder
			if len(images) != 0 :
				try :
					dir_name = self.path + "/" + request + "/" + "Images"
					os.makedirs(dir_name)
					os.chdir(dir_name)
				except :
					print("Folder already exist")
					os.chdir(dir_name)
					
			# Get all the images sources and save them
			for image in images :
				
				# Set the loop variables and update progressbar
				counter_progress += 1
				counter_name = counter_progress
				bar_length = len(images)
				progress_callback.emit("Downloading images ", counter_progress, bar_length)
				
				# Create the file if file depending on file already present in the folder
				try:
					response = requests.get(image)
					filename = str(counter_name) + ".png"
					while os.path.isfile('./{}'.format(filename)) is True :
						counter_name +=1
						filename = str(counter_name) + ".png"	
				except:
					continue

				# Write data in the file
				try:
					f = open(filename, "wb")
					f.write(response.content)
					f.close()
				except :
					continue
			# Reinit the name counter and the path for videos
			os.chdir(self.path)	
			counter_name = 1

			# Create video folder
			if len(videos) != 0 :
				try :
					dir_name = self.path + "/" + request + "/" + "Videos"
					os.makedirs(dir_name)
					os.chdir(dir_name)
				except :
					print("Folder already exist")
					os.chdir(dir_name)

			# Get videos sources, basically the same as image but for videos	
			for video in videos :
				
				counter_progress += 1
				counter_videos += 1
				counter_name = counter_progress
				bar_length = len(videos)
				progress_callback.emit("Downloading Videos ", counter_videos, bar_length)

				try:
					response = requests.get(video)
					filename = str(counter_name) + ".mp4"
					while os.path.isfile('./{}'.format(filename)) is True :
						counter_name +=1
						filename = str(counter_name) + ".mp4"	
				except:
					continue

				try:
					f = open(filename, "wb")
					f.write(response.content)
					f.close()
				except :
					continue
			# reinit the path to root folder
			os.chdir(self.path)
	
	# Multi thread caller for the downloader
	def launcher(self):

		worker = Worker(self.scrapper)
		self.threadpool.start(worker)
		worker.signals.start.connect(self.function_start)
		worker.signals.progress.connect(self.function_progress)
		worker.signals.result.connect(self.function_return)
		worker.signals.finished.connect(self.function_end)

	# Stuff when scrapper end
	def function_end(self):

		# Reset button
		self.btn_scrap.setEnabled(True)
		self.bar_progress.setVisible(False)
		os.chdir(self.path)

	# Progressbar function
	def function_progress(self, title, counter, length):

		# Change bar aspect depending on scraper progress
		self.bar_progress.setRange(0, length)
		self.bar_progress.setVisible(True)
		self.bar_progress.setValue(counter)
		self.bar_progress.setFormat("{}: {}/{}".format(title, counter, length))

	# Stuff when scrapper start
	def function_start(self):

			# Prevent the user to re-run the scrapper by disabling the button
			self.btn_scrap.setEnabled(False)

	# If something went wrong print output
	def function_return(self, output):

		print(output)

if __name__ == '__main__':

	app = QApplication(sys.argv)
	ex = InstaScrap()
	sys.exit(app.exec_())