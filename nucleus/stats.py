import os
import pandas as pd
from core import Path
from datetime import datetime

# workcenter = pd.read_excel('workcenter.xlsx')


# Track daily status trends over time


log_path = os.path.join(
	Path.USERS,
	'mcclbra',
	'mcclbra 2019-10.log'
)


class LogFileManipulations:

	# Get last login
	# Get average time logged in
	# Compare completed date with job due date
	# Get time from job start to probe email
	# Get number of completed drawings
	# Check number of times user agreement is viewed per job


	LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S,%f"
	DF_COLUMNS = ['DateTime', 'Username', 'Action']

	@staticmethod
	def get_logfile_data(path):
		"""Retrieve data from a logfile.

		Parameters
		----------
		path : str
			Absolute path to logfile.

		Returns
		-------
		data : list

		Raises
		------
		IOError
			If no such file or directory.
		EOFError
			If file is empty.

		"""
		with open(path, 'rb') as f:
			data = f.readlines()
		return data

	@staticmethod
	def get_data_from_line(line):
		"""Split and return the meaningful information of a logfile line.

		Parameters
		----------
		line : str
			Must conform to '<asctime>  INFO: <username> ~ <action>'.

		Returns
		-------
		date_and_time : datetime.datetime
		username : str
		action : str

		"""
		split_by_time = line.split('  ')
		date_and_time = datetime.strptime(
			split_by_time[0], 
			LogFileManipulations.LOG_TIME_FORMAT
		)
		info_msg = split_by_time[1].split('INFO: ')[1]
		info_msg_split = info_msg.split(' ~ ')
		username = info_msg_split[0]
		action = info_msg_split[1].strip('\r\n')
		return date_and_time, username, action		

	@staticmethod
	def df_from_logfile_lines(lines):
		"""Build a DataFrame from logfile data.

		Parameters
		----------
		lines : list
			Data retrieved from logfile.

		Returns
		-------
		df : DataFrame

		"""
		data = []
		for line in lines:
			date, user, action = LogFileManipulations.get_data_from_line(line)
			data.append([date, user, action])
		df = pd.DataFrame(data=data, columns=LogFileManipulations.DF_COLUMNS)
		return df

	@staticmethod
	def log_state_df(df):
		"""Returns a DataFrame containing user logins/logouts only.
		
		Parameters
		----------
		df : DataFrame

		"""
		return df[df['Action'].str.contains('logged')]

	@staticmethod
	def valid_login_indices(df):
		"""Returns a DataFrame of valid login/logout data.
		
		Parameters
		----------
		df : DataFrame
		
		"""
		indices = []
		previous = None
		for index, row in df.iterrows():
			if row['Action'] != previous:
				previous = row['Action']
				indices.append(index)
			else:
				del indices[-1]
				indices.append(index)
		return indices

	@staticmethod
	def sort_log_states(df):
		ins = []
		outs = []
		for index, row in df.iterrows():
			if row['Action'] == 'logged in':
				ins.append(row['DateTime'])
			else:
				outs.append(row['DateTime'])
		return ins, outs




lines = LogFileManipulations.get_logfile_data(log_path)
df = LogFileManipulations.df_from_logfile_lines(lines)
df = LogFileManipulations.log_state_df(df)
indices = LogFileManipulations.valid_login_indices(df)
df = df[df.index.isin(indices)]
ins, outs = LogFileManipulations.sort_log_states(df)
print ins, outs
print len(ins), len(outs)


