PROD_HOST = "monty.ccnmtl.columbia.edu"

def run_unit_tests(pusher):
    codir = pusher.checkout_dir()
    (out,err) = pusher.execute("pushd %s && python setup.py testgears && popd" % codir)
    return ("FAILED" not in out,out,err)

def post_rsync(pusher):
    (out,err) = pusher.execute(["ssh",PROD_HOST,"/var/www/rollo/init.sh","/var/www/rollo/"])
    (out2,err2) = pusher.execute(["ssh",PROD_HOST,"sudo","/usr/bin/supervisorctl","restart","rollo"])
    out += out2
    err += err2
    return (True,out,err)  
