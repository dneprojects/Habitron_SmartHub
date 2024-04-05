echo SUPERVISOR_TOKEN > /src/def_token.set
echo ohne > def_token.set
echo root > /def_token.set
echo root_src > /src/def_token.set
echo dot_src > ./def_token.set
echo dot > ./def_token.set
echo dot_dot > ../def_token.set
printenv SUPERVISOR_TOKEN
python smarthub.py
