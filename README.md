# box-ai-metadata-suggestions-skill

Setup:

Requirements

* Python 3.11+
* gcloud cli

You will need to set up two apps in the Box Developer Console
custom skill
From this app, you will need the client ID from the configuration tab and the primary and secondary key from the security keys tab. Create a file in the skills folder called .env.yaml and add the following:

```yaml
BOX_CLIENT_ID: your_client_id
BOX_KEY_1: your_primary_key
BOX_KEY_2: your_secondary_key
```

Custom app

This should be JWT authorization and you should set App + Enterprise Access, and make sure the `Manage AI` scope is selected. For testing, you can just check all the boxes. On the configuration page, generate a public key and save the resulting json file. Rename this json file to `metadata-extraction-jwt.json` and copy it into the skills folder

Now from the commandline, type `./deploy.sh` and hit ENTER.

From the results, in the resulting yaml, you should see something like:

```yaml
httpsTrigger:
  securityLevel: SECURE_OPTIONAL
  url: https://us-central1-box-extract-skill.cloudfunctions.net/skill
```

Copy that URL, and in the developer console, go to your custom skill app, and paste it into the invocation url field and click save.

In your Box application, navigate to the admin console and click on `Apps` in the left hand navigation. On this page, click the `Custom Apps Manager` tab and then click `Add App`. Paste in the client ID from your JWT application and enable the app. Click `Add App` again and paste in the client ID from your custom skill app.

Next navigate to the hidden url https://app.box.com/master/skills.. Here you will click `Add Skill` and paste in your client ID. You can then select a specific folder to run the skill against, and then whenever you add a new file or copy or move a new file into that folder, the invocation url will be called with the skills payload.