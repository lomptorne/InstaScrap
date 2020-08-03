import os 
import sys
import requests 
import traceback
import os.path
import json

from pathlib import Path
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
		self.threadpool.setMaxThreadCount(1)

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
			path = os.getcwd()
			url = "https://www.instagram.com/explore/tags/{}/?__a=1".format(request)
			page = requests.get(url)
			counter_progress = 0
			progress_callback.emit("Querying", counter_progress, counter_progress)

			# get the json packages from instagram or raise an error if nothing
			try :

				jsonDump = page.json()['graphql']['hashtag']['edge_hashtag_to_media']['edges']

			except KeyError:
				self.label_indicator.setText("No Result")
				self.btn_scrap.setEnabled(True)

			

			# Append the results from the json to a link list
			for node in jsonDump :
				results.append(node['node']['display_url'])

			# if there is not enough image in the first page then scroll to more results until it reachs the user input
			if len(results) <= number_pictures and len(results) > 71:
				
				while len(results) < number_pictures :

					# Modifying the url in order to scroll the pages
					urlnext  =  url + "&max_id=" + page.json()['graphql']['hashtag']['edge_hashtag_to_media']['page_info']['end_cursor']
					page = requests.get(urlnext)
					jsonDump = page.json()['graphql']['hashtag']['edge_hashtag_to_media']['edges']

					# Add the new results to the list
					for node in jsonDump :
						results.append(node['node']['display_url'])

			# Reduce the list size to make it the same number as user input
			if len(results) > number_pictures : 
				accuration = len(results) - number_pictures
				results = results[:-accuration]

			# Create the folder to contian the images
			try:
				dir_name =  path + '/{}/Images'.format(request)
				os.makedirs(dir_name)
				os.chdir(dir_name)

			except OSError:
				os.chdir(dir_name)
				print("Folder already exists")
				

			for image in results : 

				# Set the loop variables and update progressbar
				counter_progress += 1
				counter_name = counter_progress
				bar_length = len(results)
				progress_callback.emit("Downloading images ", counter_progress, bar_length)

				# Create the file if file depending on file already present in the folder
				try:
					response = requests.get(image)
					filename = str(counter_name) + ".jpg"
					while os.path.isfile('./{}'.format(filename)) is True :
						counter_name +=1
						filename = str(counter_name) + ".jpg"	
				except:
					continue

				# Write data in the file
				try:
					f = open(filename, "wb")
					f.write(response.content)
					f.close()
				except :
					sys.exit(5)
			
			# Reinit the name counter and the path and set the result
			os.chdir(self.path)	
			counter_name = 1
			result = "Done !"

		return result

	# Multi thread caller for the downloader
	def launcher(self):
		
		worker = Worker(self.scrapper)
		self.threadpool.start(worker)

		worker.signals.start.connect(self.function_start)
		worker.signals.progress.connect(self.function_progress)
		worker.signals.result.connect(self.function_return)
		worker.signals.finished.connect(self.function_end)
		worker.signals.error.connect(self.function_error)

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

		# reset the label and button
		self.label_indicator.setText("")
		self.btn_scrap.setEnabled(False)
		
	# Stuff when scrapper start
	def function_start(self):

		# Prevent the user to re-run the scrapper by disabling the button
		self.btn_scrap.setEnabled(False)
		self.label_indicator.setText("")
	
	def function_error(self):
		self.label_indicator.setText("No Results")
			
	# If something went wrong print output
	def function_return(self, output):

		self.label_indicator.setText(output)

if __name__ == '__main__':

	app = QApplication(sys.argv)
	ex = InstaScrap()
	sys.exit(app.exec_())