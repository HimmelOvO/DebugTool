import argparse
import subprocess
import os,sys
from bullet import Bullet,colors

def parse():
	parser = argparse.ArgumentParser(prog='OneProImg',
		description='e.g. %(prog)s sdm (optional) -i bcmt-registry:5000/nokia/udm/sdm:228.216.1 -t newtag -n udm01',
		usage='%(prog)s [Pod] optional: -i [BaseImage] -t [newtag] -n [namespace] -h -> help',
		epilog="El psy congroo")
	parser.add_argument("-p", "--pod", nargs='?', required=False)
	parser.add_argument("-i", "--image", nargs='?', required=False)
	parser.add_argument("-n", "--namespace", nargs='?', required=False)
	parser.add_argument("-t", "--tag", nargs='?', required=False)
	args = parser.parse_args()

	if (args.pod):
		pod = args.pod
	else:
		print("good choose start!")
		pod = getchoosepod()
	if (args.namespace):
		namespace = args.namespace
	else:
		namespace = getchoosenamespace()
	if (args.image):
		image = args.image
	else:
		image = getdefaultimage(args.pod,namespace)
	if (args.tag):
		tag = args.tag
	else:
		tag = image + "new"

	if (len(pod) > 2):
		process = pod
	else:
		process = pod + 's'
	tcnfile = 'ng' + process + '.tcn'
	if (pod == 'sdm'):
		tcnfile = 'sdm.tcn'	

	if not os.path.exists(tcnfile):
		print("No local tcn, will get it.\n")
		cptcn(pod, image, namespace, tcnfile, process)
	budocker(pod, image, tag, tcnfile)

def getchoosenamespace():
	npresult = subprocess.check_output('kubectl get namespace', shell=True)	
	npresult = npresult.split('\n')
	delist = ["NAME","credential","default","kube","ncms","kube-node-lease","gatekeeper-system","kube-public","kube-system"]	
	nplist=[]
	for np in npresult:
		if len(np) != 0:
			npinfo = np.split()
			if not npinfo[0] in delist:
				nplist.append(npinfo[0])
	cli = Bullet(
			prompt = "\nPlease choose a namespace:",
			choices = nplist,
			indent = 0,
			align = 5,
			margin = 2,
			shift = 0,
			bullet = "★",
			bullet_color=colors.bright(colors.foreground["cyan"]),
			word_color=colors.bright(colors.foreground["yellow"]),
			word_on_switch=colors.bright(colors.foreground["yellow"]),
			background_color=colors.background["black"],
			background_on_switch=colors.background["black"],
			pad_right = 5
	)

	return cli.launch()
	

def getchoosepod():
	podlist=['sdm','ee','uecm','nim','pp']
	cli = Bullet(
			prompt = "\nPlease choose a pod:",
			choices = podlist,
			indent = 0,
			align = 5,
			margin = 2,
			shift = 0,
			bullet = "★",
			bullet_color=colors.bright(colors.foreground["magenta"]),
			word_color=colors.bright(colors.foreground["blue"]),
			background_color=colors.background["cyan"],
			pad_right = 5
	)

	return cli.launch()

def getdefaultimage(pod,namespace):
	describecmd = 'kubectl describe deployments ' + namespace + '-udm' + pod + ' -n ' + namespace + ' | grep Image | grep ' +pod
	try:
		deployinfo = subprocess.check_output(describecmd, shell=True)
	except:
		print("[Error] failed to get default image tag from deployment")
		sys.exit(0)
	result =  deployinfo.split()
	return result[1]

def cptcn(pod,image,namespace,tcnfile,process):
	getpodcmd='kubectl get pod -n' + namespace + ' | grep ' + pod
	result = subprocess.check_output(getpodcmd, shell=True)
	podinfo = result.split()
	cpcmd = 'kubectl cp ' + namespace + '/' + podinfo[0] + ':/home/rtp99/99/cust_conf/' + tcnfile + ' ./' + tcnfile + ' -n' + namespace + ' -c' + pod + '-mcc'
	sedcmd1 = "sed -i '/NGC_" + process.upper() + "1[0-9]/d' "  + tcnfile
	sedcmd0 = "sed -i '/NGC_" + process.upper() + "0[2-9]/d' "+ tcnfile
	chmodcmd = 'chmod 755 ' + tcnfile
	subprocess.call(cpcmd, shell=True)
	try:
		retinfo = subprocess.check_output(sedcmd1, shell=True)
	except subprocess.CalledProcessError as er:
		print("[Error] failed to read such tcn file")
		sys.exit(1)
	subprocess.call(sedcmd0, shell=True)
	subprocess.call(chmodcmd, shell=True)

def budocker(pod,image,newname,tcnfile):
	predockerfile(tcnfile,image)
	if os.path.exists("Customdocker"):
		customdocker()
	
	try:
		subprocess.check_call("which podman", shell=True)
	except:
		exe='docker'
	else:
		exe='podman'
	finally:
		buildcmd = exe +' build -t ' + newname +' .'
		try:
			subprocess.check_call(buildcmd, shell=True)
			print("newimage build successfully:" + newname)
		except:
			print("[Error] failed to build image")
			sys.exit(2)

def predockerfile(tcnfile,image):
	binarylist = {'Sdm', 'EventExp','Uecm','Nim','ParamProv'}
	rtplibpath = ' /opt/SMAW/SMAWrtp/lib64'
	comlibpath = ' /opt/SMAW/INTP/lib64'
	combinpath = ' /opt/SMAW/INTP/bin64'
	cusergroup = 'COPY --chown=root:dba '
	
	
	file = open("Dockerfile", 'w')
	file.write("From  " + image + "\n")
	file.write("USER root\n")
	file.write('COPY --chown=root:root ' + tcnfile + ' /tmp/tcn/\n')

	list = os.listdir('./')
	for filename in list:
		filepath = os.path.join('./', filename)
		if os.path.isfile(filepath):
			if filepath.endswith('.so'):
				if "Rtp" in filename:
					file.write(cusergroup + filename + rtplibpath + "\n")
				else:
					file.write(cusergroup + filename + comlibpath + "\n")
			elif file in binarylist:
				file.write(cusergroup + filename + combinpath + "\n")
	file.close()	

def customdocker():
	allowedDockerCmds = ['COPY', 'RUN']
	with open("Dockerfile", 'a') as df, open("Customdocker", 'r') as cin:
		for l in cin:
			_l = l.strip().split()
			if _l[0].upper() in allowedDockerCmds:
				df.write(l)
			else:
				print("Skip unknown line: %s" % l.strip())


def main():
	parse()

	print('Congratulations!')
	
	

if __name__=='__main__':
    main()





