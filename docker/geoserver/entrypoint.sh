#!/bin/bash
set -e

source /root/.bashrc

# control the value of DOCKER_HOST_IP variable
if [ -z ${DOCKER_HOST_IP} ]
then

    echo "DOCKER_HOST_IP is empty so I'll run the python utility \n"
    echo export DOCKER_HOST_IP=`python3 /usr/local/tomcat/tmp/get_dockerhost_ip.py` >> /root/.override_env
    echo "The calculated value is now DOCKER_HOST_IP='$DOCKER_HOST_IP' \n"

else

    echo "DOCKER_HOST_IP is filled so I'll leave the found value '$DOCKER_HOST_IP' \n"

fi

# control the values of LB settings if present
if [ ${GEONODE_LB_HOST_IP} ]
then

    echo "GEONODE_LB_HOST_IP is filled so I replace the value of '$DOCKER_HOST_IP' with '$GEONODE_LB_HOST_IP' \n"
    echo export DOCKER_HOST_IP=${GEONODE_LB_HOST_IP} >> /root/.override_env

fi

if [ ${GEONODE_LB_PORT} ]
then

    echo "GEONODE_LB_PORT is filled so I replace the value of '$PUBLIC_PORT' with '$GEONODE_LB_PORT' \n"
    echo export PUBLIC_PORT=${GEONODE_LB_PORT} >> /root/.override_env

fi

if [ ! -z "${GEOSERVER_JAVA_OPTS}" ]
then

    echo "GEOSERVER_JAVA_OPTS is filled so I replace the value of '$JAVA_OPTS' with '$GEOSERVER_JAVA_OPTS' \n"
    JAVA_OPTS=${GEOSERVER_JAVA_OPTS}

fi

# control the value of NGINX_BASE_URL variable
if [ -z `echo ${NGINX_BASE_URL} | sed 's/http:\/\/\([^:]*\).*/\1/'` ]
then
    echo "NGINX_BASE_URL is empty so I'll use the static nginx hostname \n"
    # echo export NGINX_BASE_URL=`python3 /usr/local/tomcat/tmp/get_nginxhost_ip.py` >> /root/.override_env
    # TODO rework get_nginxhost_ip to get URL with static hostname from nginx service name
    # + exposed port of that container i.e. http://geonode:80
    echo export NGINX_BASE_URL=http://geonode:80 >> /root/.override_env
    echo "The calculated value is now NGINX_BASE_URL='$NGINX_BASE_URL' \n"
else
    echo "NGINX_BASE_URL is filled so I'll leave the found value '$NGINX_BASE_URL' \n"
fi

# set basic tagname
TAGNAME=( "baseUrl" )

if ! [ -f ${GEOSERVER_DATA_DIR}/security/auth/geonodeAuthProvider/config.xml ]
then

    echo "Configuration file '$GEOSERVER_DATA_DIR'/security/auth/geonodeAuthProvider/config.xml is not available so it is gone to skip \n"

else

    # backup geonodeAuthProvider config.xml
    cp ${GEOSERVER_DATA_DIR}/security/auth/geonodeAuthProvider/config.xml ${GEOSERVER_DATA_DIR}/security/auth/geonodeAuthProvider/config.xml.orig
    # run the setting script for geonodeAuthProvider
    /usr/local/tomcat/tmp/set_geoserver_auth.sh ${GEOSERVER_DATA_DIR}/security/auth/geonodeAuthProvider/config.xml ${GEOSERVER_DATA_DIR}/security/auth/geonodeAuthProvider/ ${TAGNAME} > /dev/null 2>&1

fi

# backup geonode REST role service config.xml
cp "${GEOSERVER_DATA_DIR}/security/role/geonode REST role service/config.xml" "${GEOSERVER_DATA_DIR}/security/role/geonode REST role service/config.xml.orig"
# run the setting script for geonode REST role service
/usr/local/tomcat/tmp/set_geoserver_auth.sh "${GEOSERVER_DATA_DIR}/security/role/geonode REST role service/config.xml" "${GEOSERVER_DATA_DIR}/security/role/geonode REST role service/" ${TAGNAME} > /dev/null 2>&1

# set oauth2 filter tagname
TAGNAME=( "accessTokenUri" "userAuthorizationUri" "redirectUri" "checkTokenEndpointUrl" "logoutUri" )

# backup geonode-oauth2 config.xml
cp ${GEOSERVER_DATA_DIR}/security/filter/geonode-oauth2/config.xml ${GEOSERVER_DATA_DIR}/security/filter/geonode-oauth2/config.xml.orig
# run the setting script for geonode-oauth2
/usr/local/tomcat/tmp/set_geoserver_auth.sh ${GEOSERVER_DATA_DIR}/security/filter/geonode-oauth2/config.xml ${GEOSERVER_DATA_DIR}/security/filter/geonode-oauth2/ "${TAGNAME[@]}" > /dev/null 2>&1

# set global tagname
TAGNAME=( "proxyBaseUrl" )

# backup global.xml
cp ${GEOSERVER_DATA_DIR}/global.xml ${GEOSERVER_DATA_DIR}/global.xml.orig
# run the setting script for global configuration
/usr/local/tomcat/tmp/set_geoserver_auth.sh ${GEOSERVER_DATA_DIR}/global.xml ${GEOSERVER_DATA_DIR}/ ${TAGNAME} > /dev/null 2>&1

# set correct amqp broker url
sed -i -e 's/localhost/rabbitmq/g' ${GEOSERVER_DATA_DIR}/notifier/notifier.xml

# exclude wrong dependencies
sed -i -e 's/xom-\*\.jar/xom-\*\.jar,bcprov\*\.jar/g' /usr/local/tomcat/conf/catalina.properties

# J2 templating for this docker image we should also do it for other configuration files in /usr/local/tomcat/tmp

declare -a geoserver_datadir_template_dirs=("geofence")

for template in in ${geoserver_datadir_template_dirs[*]}; do
    #Geofence templates
    if [ "$template" == "geofence" ]; then
      cp -R /templates/$template/* ${GEOSERVER_DATA_DIR}/geofence

      for f in $(find ${GEOSERVER_DATA_DIR}/geofence/ -type f -name "*.j2"); do
          echo -e "Evaluating template\n\tSource: $f\n\tDest: ${f%.j2}"
          /usr/local/bin/j2 $f > ${f%.j2}
          rm -f $f
      done

    fi

done

# copy printing settings
cp /templates/printing/print_header.png ${GEOSERVER_DATA_DIR}/printing/print_header.png
cp /templates/printing/config.yaml ${GEOSERVER_DATA_DIR}/printing/config.yaml
cp /templates/printing/config.yaml.ms2 ${GEOSERVER_DATA_DIR}/printing/config.yaml.ms2

# start tomcat
exec env JAVA_OPTS="${JAVA_OPTS}" catalina.sh run
