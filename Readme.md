# **CL4 Archiver**
Archive 4chan posts to disk with optional media conversion.

### **installation**

Globally
```
pip3 install git+https://github.com/arx8x/4Chan-Archiver
```

Or to venv

```
git clone https://github.com/arx8x/4Chan-Archiver
cd 4Chan-Archiver
python3 -m venv venv
source venv/bin/activate/
```

**Note**: `ffmpeg` should be installed to enable media conversion

### **Usage**

Supply the url as the last argument.    

&nbsp;    
Archive a thread using the provided URL    

`cl4archiver https://boards.4channel.org/wsg/thread/4393506`    
&nbsp;


Update all previously archived threads without media conversion

`cl4archiver -u -n`    
&nbsp; 

Archive a thread with the provided url and run 8 media downloads and conversion in parallel to "/tmp/archives" directory

`cl4archiver -p 8 -o /tmp/archives/ -n https://boards.4channel.org/wsg/thread/4393506`

**Options**
```
-n, --no-convert           explicitly disable media conversion  
-r, --remove-orig          remove original file after conversion (currently just .webm)  
-b, --binpath              supply path to look for binaries (ffmpeg)
-o, --output               output/working directory to work on
-u, --update               check all posts previous archived and update them
                           if new content is found
-p, --parallel             number of threads to use for media (default: 1)

```
