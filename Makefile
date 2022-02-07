up:
	# bring up the services
	docker-compose up -d

build:
	docker-compose build django
	docker-compose build celery

sync:
	# set up the database tablea
	docker-compose run django python manage.py makemigrations --noinput
	docker-compose exec django python manage.py migrate account --noinput
	docker-compose exec django python manage.py migrate undp_bougainville --noinput
	docker-compose run django python manage.py migrate --noinput

wait:
	sleep 5

logs:
	docker-compose logs --follow

geonode_log:
	docker-compose exec django bash -c "cat /var/log/geonode.log"

down:
	docker-compose down

test:
	docker-compose run django python manage.py test --failfast

reset: down up wait sync

hardreset: pull build reset
