# **CL4 Archiver**
Archive 4chan posts to disk with optional media conversion.

### **installation**

```
git clone https://github.com/arx8x/4Chan-Archiver
cd 4Chan-Archiver
python3 -m venv cl4archiver
source cl4archiver/bin/activate/
```
`ffmpeg` should be installed to enable media conversion

### **Usage**

Supply the url as the last argument.

`cl4archiver https://boards.4channel.org/wsg/thread/4393506`

`cl4archiver -u` 

`cl4archiver -p 8 -o /tmp/archives/ -n https://boards.4channel.org/wsg/thread/4393506`

**Options**
```
-n, --no-convert           explicitly disable media conversion  
-b, --binpath              supply path to look for binaries
-o, --output               output/working directory to work on
-u, --update               check all posts previous archived and update them
                           if new content is found
-p, --parallel             number of threads to use for media (default: 1)

```
