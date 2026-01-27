# BofL Analyzer

## Development Process Documentation

### Gmail Setup

In a professional setting (G-Suite / Google Workspace), we would use a Service Account. This is a special "robot" account that uses a key file to authenticate instantly with organization email via API, with zero human interaction.

For a standard free Gmail account (@gmail.com), there is no way to get credentials purely via an API call without a human interaction to authenticate. For this project, we used this method. Also, since the program will read specifically from one targeted Gmail account, we will not use the `Sign in with Google` method for getting the authentication key. Therefore, we have left with two options:

1. Generate the authentication token manually using Google's developer tool and save it.

2. Getting the authentication token automatically using a script that prompt us to authenticate via the browser. This method is the one we used.

#### Here is how the second method will work

1. We run a script locally (i.e `backend/src/gmail_auth.py`). It opens a browser, we sign in to targeted Gmail account and click "Allow". Then, we will save the authentication token in an `auth_token.json` file.

2. Our backend uses that `auth_token.json` forever (it automatically refreshes itself).

#### How we can do it?

Go to the Google Cloud Console (console.cloud.google.com) and select your project.

##### A. Configure the Consent Screen in GCP project

1. In left sidebar, go to APIs & Services > OAuth consent screen

2. In `User Type`, select External to allow anyone (Internal is only for emails within a organization/company).

3. Click `Create`. Then give the app a name and a customer support email.

4. You might also be asked to provide a developer email so GCP team can contact you regarding this auth.

##### B. Create OAuth Credentials

1. Go to APIs & Services > Credentials.

2. Click `CREATE CREDENTIALS` at the top and select OAuth client ID.

3. Application Type: Select Desktop App (Because we are running a script that needs to pop up a browser window once).

4. Give it a name and your email for GCP team to contact you.

5. Click Create.

6. Download the JSON file. Rename it to `auth_credentials.json` and put it in the backend folder.

##### C. Add Test Users

- Since our app is "External" and unverified, it will only work for emails we allowed called `Test Users`.

1. In left sidebar, go to APIs & Services > OAuth consent screen > Audience.

2. Under `Test users`, click `Add Users` and type the exact gmail address we will access its emails.
