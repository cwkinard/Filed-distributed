from __future__ import print_function
from apiclient import errors
from datetime import datetime
import httplib2
import os
import sys
import logging
import re

from apiclient import discovery
from apiclient.http import MediaFileUpload
import oauth2client
from oauth2client import client
from oauth2client import tools


SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Filed'



class Drive(object):
    def __init__(self, flags):

	self._logger = logging.getLogger(__name__)
	self.flags = flags

        self.credentials = self.get_credentials()
        self.http = self.credentials.authorize(httplib2.Http())    
        self.service = discovery.build('drive', 'v2', http=self.http)
    
    @classmethod
    def get_credentials(cls):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        credential_path = os.path.join('.credentials',
                                       'drive.json')

        store = oauth2client.file.Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            #if flags:
            credentials = tools.run_flow(flow, store, self.flags)
            #else: # Needed only for compatibility with Python 2.6
                #credentials = tools.run(flow, store)
            print('Storing credentials to ' + credential_path)
        return credentials

    def get_latest_from_folder(self, folder_id):
        """Retrieve date of the latest file in folder.

        Args:
            folder_id: ID of the folder to retrieve latest file name from.
        """
        try:
            param = {}
            children = self.service.children().list(folderId=folder_id,
	   		                            orderBy='title desc', **param).execute()
	    
	    date = datetime.strptime('20000101', "%Y%m%d").date() 
	    for child in children.get('items', []): 
	        file = self.service.files().get(fileId=child['id']).execute()

	        match = re.search(r'\d{4}-\d{2}-\d{2}', file['title'])
	        if match is not None:
                    date = datetime.strptime(match.group(), '%Y-%m-%d').date()
		    return date
		    break
	    return date

	except errors.HttpError, error:
            print('An error occurred: %s' % error)		

    def add_file_to_folder(self, file_name, file_path, folder_id):
        """Insert new file.

        Args:
          service: Drive API service instance.
          title: Title of the file to insert, including the extension.
          description: Description of the file to insert.
          parent_id: Parent folder's ID.
          mime_type: MIME type of the file to insert.
          filename: Filename of the file to insert.
        Returns:
          Inserted file metadata if successful, None otherwise.
        """

	self._logger.debug("file_name: '%s', file_path: '%s' ", file_name, file_path)

        media_body = MediaFileUpload(file_path, mimetype='application/pdf', resumable=False)
        body = {
          'title': file_name,
          'mimeType': 'application/pdf',
	  'parents': [{'id': folder_id}]
        }

        try:
          file = self.service.files().insert(
              body=body,
              media_body=media_body).execute()

          # Uncomment the following line to print the File ID
          # print('File ID: %s' % file['id'])

          return file
        except errors.HttpError, error:
          self._logger.warn(error)
	  return None

