import sys, time, java.lang.System

lineSeparator = java.lang.System.getProperty('line.separator')
clusterInfoList = {}
timeClusterRestart = int(sys.argv[0])
timeClusterRestartCount = 5  # В сек, используется для ожидания между запросами состояния кластера в while в checkStateAndRunCommand
timeClusterRestart = timeClusterRestart / timeClusterRestartCount
runApp = []


def getClusterInfo(localLineSeparator):
	clusters = AdminControl.queryNames('type=Cluster,*')
	if clusters != '':
		for cluster in clusters.split(localLineSeparator):
			# AdminConfig.showAttribute(cluster, 'name')
			first = cluster.find("name=")
			clusterName = cluster[first + 5: cluster.find(",", first + 4)]
			clusterInfoList[clusterName] = cluster
	else:
		print("Cluster is not found")
		sys.exit(1)


def getSharedInfo(clusterName, localLineSeparator, execFunc, arrayForAppInfo=[]):
	# Принимает в качестве агрумента execFunc тело ф-ии. Нужно для запуска getStateClusterSrv и getStateClusterApp
	cell = AdminConfig.list('Cell')
	cellName = AdminConfig.showAttribute(cell, 'name')
	clusterId = AdminConfig.getid('/ServerCluster:' + clusterName + '/')
	clusterList = AdminConfig.list('ClusterMember', clusterId)
	servers = clusterList.split(localLineSeparator)
	for serverId in servers:
		serverName = AdminConfig.showAttribute(serverId, 'memberName')
		nodeName = AdminConfig.showAttribute(serverId, 'nodeName')
		execFunc(cellName, nodeName, serverName, clusterName, arrayForAppInfo)


def getStateClusterSrv(localCellName, localNodeName, localServerName, localClusterName, arrayForAppInfo=[]):
	serverStatus = AdminControl.completeObjectName(
		'cell=' + localCellName + ',node=' + localNodeName + ',name=' + localServerName + ',type=Server,*')
	if (serverStatus != ""):
		serverState = AdminControl.getAttribute(serverStatus, 'state')
	else:
		serverState = " STOPPED"
	print("Status " + localServerName + " on Cluster " + localClusterName + " is " + serverState)


def getStateClusterApp(localCellName, localNodeName, localServerName, localClusterName, arrayForApplication):
	apps = AdminControl.queryNames(
		'type=Application,cell=' + localCellName + ',node=' + localNodeName + ',process=' + localServerName + ',*').splitlines()
	for app in apps:
		appName = AdminControl.getAttribute(app, 'name')
		arrayForApplication.append(appName)


def restartCluster(localClusterInfoList, localLineSeparator, timeoutClusterRestart, timeoutClusterRestartCount):
	runStatusCluster = "running"
	stopStatusCluster = "stopped"
	runCommandStop = "stop"
	runCommandStart = "start"
	stringPartClusterState = "websphere.cluster."

	def checkStateAndRunCommand(localLineSeparator, dictKey, dictValue, preClusterStatusState, afterClusterStatusState,
								runCommand, localTimeoutClusterRestart, localTimeoutClusterRestartCount,
								localStringPartClusterState):
		state = AdminControl.getAttribute(dictValue, 'state')

		def workClusterStateStatus(string, partString):
			result = string.replace(partString, "").upper()
			return result

		print(
			"Try run command " + runCommand.upper() + " for cluster " + dictKey + localLineSeparator + "Timeout = " + str(
				localTimeoutClusterRestart * localTimeoutClusterRestartCount) + " sec")
		if state.find(preClusterStatusState) != -1:
			AdminControl.invoke(dictValue, runCommand)
			clusterState = ""
			while 1:
				clusterState = AdminControl.getAttribute(dictValue, 'state')
				localTimeoutClusterRestart -= 1
				if clusterState.find(afterClusterStatusState) != -1:
					print(dictKey + " is " + workClusterStateStatus(clusterState, localStringPartClusterState))
					break
				if localTimeoutClusterRestart == 0:
					print("Timeout is expired! Cluster" + dictKey + " is " + workClusterStateStatus(clusterState,
																									localStringPartClusterState))
					getSharedInfo(dictKey, localLineSeparator, getStateClusterSrv)
					sys.exit(1)
				time.sleep(localTimeoutClusterRestartCount)
			return 0
		else:
			print(dictKey + " cannot be stopped. Current state is " + workClusterStateStatus(state,
																							 localStringPartClusterState))
			getSharedInfo(dictKey, localLineSeparator, getStateClusterSrv)
			return 1

	for key, value in localClusterInfoList.items():
		print("Work with Cluster " + key)
		stopCluster = checkStateAndRunCommand(localLineSeparator, key, value, runStatusCluster, stopStatusCluster,
											  runCommandStop, timeoutClusterRestart, timeoutClusterRestartCount,
											  stringPartClusterState)
		if stopCluster == 0:
			startCluster = checkStateAndRunCommand(localLineSeparator, key, value, stopStatusCluster, runStatusCluster,
												   runCommandStart, timeoutClusterRestart, timeoutClusterRestartCount,
												   stringPartClusterState)
			print("Run check application status")
			time.sleep(5)
			getSharedInfo(key, localLineSeparator, getStateClusterApp, runApp)


# В Jython 2.1 нет ф-ии dict()
def dict(sequence):
	resultDict = {}
	for key, value in sequence:
		resultDict[key] = value
	return resultDict


def main():
	getClusterInfo(lineSeparator)
	if len(clusterInfoList) > 0:
		restartCluster(clusterInfoList, lineSeparator, timeClusterRestart, timeClusterRestartCount)
	allApp = AdminApp.list().split(lineSeparator)
	print("Installed Apps:")
	print(allApp)
	# stopApp = list(set(allApp) - set(runApp)) Работа с множествами поддерживается с jython 2.3, удаляем дубли через словарь
	allRunApp = list(dict([(item, None) for item in runApp]).keys())
	# Не проверяем устаноку и запуск DefaultApplication
	if ("DefaultApplication" in allRunApp):
		allRunApp.remove("DefaultApplication")
	if ("DefaultApplication" in allApp):
		allApp.remove("DefaultApplication")
	#TODO заменить работу с вложенным циклом
	# В jython 2.3 нет set
	# stopApp = list(set(allApp) ^ set(allRunApp))
	if len(allApp) > 1:
		stopApp = []
		for obj in allApp:
			stopApp.append(obj)
			if obj in allRunApp:
				stopApp.remove(obj)
		if len(stopApp) > 0:
			print("Detected not running applications: " + " ".join(stopApp))
			sys.exit(1)
		else:
			allRunApp.remove("ibmasyncrsp")
			print("List started application: " + " ".join(allRunApp))


main()
