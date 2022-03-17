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

`python3 main.py https://boards.4channel.org/wsg/thread/4393506`

**Options**
```
-n, --no-convert           explicitly disable media conversion  
-b, --binpath              supply path to look for binaries
-o, --output               output/working directory to work on
-u, --update               check all posts previous archived and update them
                           if new content is found

```
