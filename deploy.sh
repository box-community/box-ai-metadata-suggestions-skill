#!/bin/bash

cf_name=""
cloud_functions=("oidc_login" "lti_launch" "auth_redirect" "box" "jwks")

function cf_deploy {
    cd $cf_name
    gcloud functions deploy $cf_name --runtime python311 --trigger-http --allow-unauthenticated
    cd ..
}

if [ $# -eq 1 ]
then
    echo $1
    cf_name=$1
    cf_deploy
else
    for cf_name in ${cloud_functions[@]}; do
        echo $cf_name
        cf_deploy
    done
fi