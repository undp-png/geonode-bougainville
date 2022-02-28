# Bougainville Natural Resources Hub

A customised Geonode for creating an open-access online web portal to support mapping and monitoring of the environment and sustainable use of natural resources in Bougainville.

---
![Landing Page](hero_landing_bougainville_demo.png)

## Table of Contents

- [Installation](#installation)
- [Run the instance in development mode](#run-the-instance-in-development-mode)
- [Run the instance on a public site](#run-the-instance-on-a-public-site)
- [Stop the Docker Images](#stop-the-docker-images)
- [Backup and Restore from Docker Images](#backup-and-restore-the-docker-images)
- [Recommended: Track your changes](#recommended-track-your-changes)
- [Hints: Configuring `requirements.txt`](#hints-configuring-requirementstxt)
- [Automating Deployment](#automatic-deployment)
- [Mail Server Setup](#setting-up-a-mail-server)
- [Custom Changes: Differences From Default Geonode](#project-customisations)


## Installation

You need Docker 1.12 or higher, get the latest stable official release for your platform.

1. Prepare the Environment

    ```bash
    git clone https://github.com/GeoNode/geonode-project.git -b <your_branch>
    ```

2. Run `docker-compose` to start it up (get a cup of coffee or tea while you wait)

    ```bash
    docker-compose build --no-cache
    docker-compose up -d
    ```

    ```bash
    set COMPOSE_CONVERT_WINDOWS_PATHS=1
    ```

    before running `docker-compose up`

3. Access the site on http://localhost/

## Run the instance in development mode

### Use dedicated docker-compose files while developing

**NOTE**: In this example we are going to keep localhost as the target IP for GeoNode

  ```bash
  docker-compose -f docker-compose.development.yml -f docker-compose.development.override.yml up
  ```

## Run the instance on a public site

### Preparation of the image (First time only)

**NOTE**: In this example we are going to publish to the public IP http://123.456.789.111

```bash
vim .env
  --> replace localhost with 123.456.789.111 everywhere
```

### Setting up a mail-server

The docker-compose production override file (docker-compose.prod.yml) includes a mailserver to make inviting users possible.
Setting this up takes a bit of work. The basic process is outlined on in the [documentation for mailserver](https://docker-mailserver.github.io/docker-mailserver/edge/examples/tutorials/basic-installation/).

The steps are as follows:

1. Create containers\volumes with `docker-compose -f docker-compose.yml -f docker-compose.prod.yml build mailserver`
2. Setup at least one account on the mailserver `docker run --rm -v "/mnt/efs/fs1/dms/config:/tmp/docker-mailserver/" docker.io/mailserver/docker-mailserver setup email add <user>@bougainville-nr.org <user_password>`
3. Setup [DKIM](https://docker-mailserver.github.io/docker-mailserver/edge/config/best-practices/dkim/) keys `docker run --rm -v "/mnt/efs/fs1/dms/config:/tmp/docker-mailserver/" docker.io/mailserver/docker-mailserver setup config dkim keysize 2048`
4. Configure DNS as follows:
   1. Add host=`mail` subdomain
   2. Add [SPF](https://docker-mailserver.github.io/docker-mailserver/edge/config/best-practices/spf/) record host=@ value=`v=spf1 mx ~all`
   3. Add [DMARC](https://docker-mailserver.github.io/docker-mailserver/edge/config/best-practices/dmarc/) record host=`_dmarc` value=`v=DMARC1; p=none; rua=mailto:<user>@bougainville-nr.org; ruf=mailto:<user>@bougainville-nr.org; sp=quarantine; ri=86400`
   4. Add [DKIM](https://docker-mailserver.github.io/docker-mailserver/edge/config/best-practices/dkim/) record host=`mail._domainkey`  `v=DKIM1; h=sha256; k=rsa; p=<get key from /mnt/efs/fs1/dms/config/opendkim/keys/bougainville-nr.org/mail.txt>`
   5. Add MX record host=@ value=`mail.bougainville-nr.org`
5. Edit Environment file as follows
```dotenv
EMAIL_ENABLE=True
...
DJANGO_EMAIL_HOST=mail
DJANGO_EMAIL_PORT=25
DJANGO_EMAIL_HOST_USER=<user>@<yourdomain>
DJANGO_EMAIL_HOST_PASSWORD=<password>
DJANGO_EMAIL_USE_TLS=True
DJANGO_EMAIL_USE_SSL=False
```

### Startup the image

```bash
docker-compose up --build -d
```

### Stop the Docker Images

```bash
docker-compose stop
```

### Fully Wipe-out the Docker Images

**WARNING**: This will wipe out all the repositories created until now.

**NOTE**: The images must be stopped first

```bash
docker system prune -a
```

## Backup and Restore from Docker Images

### Run a Backup

```bash
SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./undp_bougainville/br/backup.sh $BKP_FOLDER_NAME
```

- BKP_FOLDER_NAME:
  Default value = backup_restore
  Shared Backup Folder name.
  The scripts assume it is located on "root" e.g.: /$BKP_FOLDER_NAME/

- SOURCE_URL:
  Source Server URL, the one generating the "backup" file.

- TARGET_URL:
  Target Server URL, the one which must be synched.

e.g.:

```bash
docker exec -it django4undp_bougainville sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./undp_bougainville/br/backup.sh $BKP_FOLDER_NAME'
```

### Run a Restore

```bash
SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./undp_bougainville/br/restore.sh $BKP_FOLDER_NAME
```

- BKP_FOLDER_NAME:
  Default value = backup_restore
  Shared Backup Folder name.
  The scripts assume it is located on "root" e.g.: /$BKP_FOLDER_NAME/

- SOURCE_URL:
  Source Server URL, the one generating the "backup" file.

- TARGET_URL:
  Target Server URL, the one which must be synched.

e.g.:

```bash
docker exec -it django4undp_bougainville sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./undp_bougainville/br/restore.sh $BKP_FOLDER_NAME'
# if restoring has failed 
docker exec -it db4undp_bougainville sh -c 'psql -f /$BKP_FOLDER_NAME/undp_bougainville/br/fix_backup.sql'
docker exec -it db4undp_bougainville sh -c 'psql -f /$BKP_FOLDER_NAME/undp_bougainville/br/postfix_geoapps_backup.sql'
```

## Recommended: Track your changes

Step 1. Install Git (for Linux, Mac or Windows).

Step 2. Init git locally and do the first commit:

```bash
git init
git add *
git commit -m "Initial Commit"
```

Step 3. Set up a free account on github or bitbucket and make a copy of the repo there.

## Hints: Configuring `requirements.txt`

You may want to configure your requirements.txt, if you are using additional or custom versions of python packages. For example

```python
Django==2.2.12
git+git://github.com/<your organization>/geonode.git@<your branch>
```

## Automatic deployment

Install node, pm2 and webhooks. PM2 runs our webhooks.

```sh
sudo apt-get install webhook
sudo apt-get install -y nodejs
sudo npm install pm2 -g 
```
Create a hooks.json file.

```json
[
  {
    "id": "redeploy-webhook",
    "execute-command": "/opt/undp_bougainville/redeploy.sh",
    "command-working-directory": "/opt/undp_bougainville/",
    "pass-arguments-to-command":
    [
      {
        "source": "payload",
        "name": "user_name"
      }
    ],
    "response-message": "Executing redeploy script",
    "trigger-rule":
    {
      "match":
      {
        "type": "value",
        "value": "<secret key>",
        "parameter":
        {
          "source": "header",
          "name": "X-Gitlab-Token"
        }
      }
    }
  }
]
```

Copy Letsencrpyt certs and run 
```bash
docker cp -L undp_bougainville_letsencrypt_1:/geonode-certificates/production/live/<machine>/fullchain.pem ~/fullchain.pem
docker cp -L undp_bougainville_letsencrypt_1:/geonode-certificates/production/live/<machine>/privkey.pem ~/privkey.pem
```

`pm2 start ecosystem.config.js`

Visit [Gitlab](https://gitlab.com/mammoth-geospatial/undp/undp_bougainville/-/hooks) setup hook to run on merge-requests and pushs.

## Project Customisations

### Higher Resolution Thumbnails
The core Geonode project sets thumbnail resolution at 240x180, this leads to fairly fuzzy images on the homepage and lists.
We have changed the behaviour to extract the size of the resolution directly from the `THUMBNAIL_GENERATOR_DEFAULT_SIZE` 
in the `settings.py` file. For example default used in our project is.

```python
...
THUMBNAIL_GENERATOR_DEFAULT_SIZE = {"width": 420, "height": 350}
...
```
We have made four changes from the default geonode project, these changes may require reversing or updating to ensure 
future compatibility.

- First we required a new endpoint `base/<resource_id>/thumbnail_upload_large/` which overrides the previous `base/<resource_id>/thumbnail_upload/` endpoint.
- Secondly a number of templates referring the old url have been updated.
- Third we have added a new field to the ResourceBase model and a new model CuratedThumbnailLarge for our new thumbnails.
- Finally we have patched the format_objects method in the API models to use this new model.

