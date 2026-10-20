#!/usr/bin/env python3
"""Download official Minecraft; use ARM LWJGL natives and built-in demo mode only."""
from pathlib import Path
import hashlib, json, urllib.request, os
import minecraft_launcher_lib as m
root=Path.home()/'minecraft-lab/demo'
version='26.3'
m.install.install_minecraft_version(version, str(root))
options=m.utils.generate_test_options()
options.update({'demo':True,'executablePath':'/usr/lib/jvm/java-25-openjdk-arm64/bin/java','jvmArguments':['-Xms512M','-Xmx4096M'],'customResolution':True,'resolutionWidth':'854','resolutionHeight':'480'})
cmd=m.command.get_minecraft_command(version,str(root),options)
idx=cmd.index('-cp')+1
classpath=cmd[idx].split(':')
for i,entry in enumerate(classpath):
    if '/org/lwjgl/' not in entry or not entry.endswith('-natives-linux.jar'): continue
    old=Path(entry); new=old.with_name(old.name.replace('-natives-linux.jar','-natives-linux-arm64.jar'))
    rel=str(new.relative_to(root/'libraries'))
    url='https://repo.maven.apache.org/maven2/'+rel
    if not new.exists():
        data=urllib.request.urlopen(url).read()
        checksum=urllib.request.urlopen(url+'.sha1').read().decode().strip()
        assert hashlib.sha1(data).hexdigest()==checksum, new.name
        new.write_bytes(data)
    classpath[i]=str(new)
cmd[idx]=':'.join(classpath)
(root/'demo-command.json').write_text(json.dumps(cmd))
(root/'options.txt').write_text('renderDistance:4\nsimulationDistance:5\nmaxFps:60\nenableVsync:false\ngraphicsMode:0\nclouds:false\nparticles:2\nguiScale:2\npauseOnLostFocus:false\n')
print('Demo command prepared for Minecraft',version,'with ARM LWJGL natives')
