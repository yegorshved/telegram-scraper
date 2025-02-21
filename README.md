# telegram-scraper

To run this program you'll need a `config.ini` file, 
this file should have the following contents:
```
[pyrogram]
api_id = your id
api_hash = your hash
[info]
phonenumber = your phone number
password = your cloud password (if you have one)
```
or you can hard-code this info inside `main.py`

# program puprose

This program will retrieve all information about your contacts:
- all profile photos
- all profile stories (archived)
- all information in profile (birth date, phonenumber, bio, etc)

It will create a folder using path from `base_path` global variable and inside this folder it will create your contacts' folders with a corresponding info.
