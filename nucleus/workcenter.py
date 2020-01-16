#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd
from errors import ColumnError, InvalidDatesError, EmptyModelError


__author__ = 'Brandon McCleary'


class WorkCenterManipulations(object):
	"""
	Provides ``DataFrame`` manipulation functions for work center spreadsheets 
	that are exported from AX2009 Live.

	"""

	@staticmethod
	def check_reqd_cols(df, reqd_cols):
		"""Verify that a ``DataFrame`` contains a ``list`` of column names.

		Parameters
		----------
		df : DataFrame
		reqd_cols : list

		Raises
		------
		ColumnError
			DataFrame does not contain all `reqd_cols`. The missing columns are 
			sent with the error.

		"""
		missing_cols = [
			col for col in reqd_cols
			if col not in df.columns
		]
		if len(missing_cols) > 0:
			raise ColumnError(missing_cols)


	@staticmethod
	def drop_extra_cols(df, reqd_cols):
		"""Remove non-essential columns from a ``DataFrame``.

		Parameters
		----------
		df : DataFrame
		reqd_cols : list

		"""
		for col in df.columns:
			if col not in reqd_cols:
				df.drop(col, axis=1, inplace=True)


	@staticmethod
	def drop_keyword_condition(df, target_col, keyword, condition='mismatch'):
		"""Conditionally remove the rows of a ``DataFrame``.

		The removal is dependent upon the `condition`, which dictates whether to
		drop rows with exact `keyword` matches or mismatches.

		Parameters
		----------
		df : DataFrame

		target_col : str
			Column where condition is checked.
			
		keyword : str
		condition : {'mismatch', 'match'}, optional

		Raises
		------
		EmptyModelError
			All rows in `df` were removed.

		"""
		if condition == 'mismatch':
			items = [
				index for index, row in df.iterrows()
				if row[target_col] != keyword
			]
		else:
			items = [
				index for index, row in df.iterrows()
				if row[target_col] == keyword
			]
		df.drop(items, inplace=True)
		if len(df.index) == 0:
			raise EmptyModelError()


	@staticmethod
	def format_date_col(df, target_col, dformat='%m/%d/%Y'):
		"""Modify the date format of a ``DataFrame`` column.

		Parameters
		----------
		df : DataFrame
		target_col : str
		dformat : str
			Optional

		Raises
		------
		InvalidDatesError
			`target_col` contains invalid (NaT) or missing (NaN) dates. The 
			indices for all invalid dates are passed to the exception and can be
			accessed via its message attribute.

		""" 
		invalid = []
		for index, row in df.iterrows():
			try:
				# First, check for invalid dates
				row[target_col].strftime(dformat)
			except (AttributeError, ValueError):
				invalid.append(index)
		if len(invalid) > 0:
			raise InvalidDatesError(invalid)

		# Modify contents
		df[target_col] = df[target_col].apply(lambda x: x.strftime(dformat))


	@staticmethod
	def jobs(df):
		"""Get all unique job numbers from a ``DataFrame``.

		Parameters
		----------
		df : DataFrame

		Returns
		-------
		set
		
		"""
		return {row['WC line alias'][:6] for index, row in df.iterrows()}


	@staticmethod
	def dict_of_df_subs(df, target_col, keywords):
		"""Get a dictionary of subsampled ``DataFrames``.

		The ``DataFrame`` subsamples are divided per `keyword`. If `df` contains
		`keyword` at `target_col`, that row is saved to the corresponding 
		`keyword` dictionary.
		
		Parameters
		----------
		df : DataFrame
		target_col : str
		keywords : list or set

		Returns
		-------
		subsets : dict

		"""
		subsets = {}
		for item in keywords:
			subsets[item] = df[df[target_col].str.contains(item)]
		return subsets


	@staticmethod
	def df_sub_from_indices(df, indices):
		"""Get a subsampled ``DataFrame`` an index list.

		Parameters
		----------
		df : DataFrame
		indices : list

		"""
		return df[df.index.isin(indices)]


	@staticmethod
	def format_work_instructions(row):
		return '%s\n\nBudgeted Hours: %s' % (
			row['Work Center Instructions'],
			str(row['Budgeted hours'])
		)


if __name__ == '__main__':
	pass