import pathlib
here = pathlib.Path(__file__).parent
src = (here/'index.src.html').read_text()
eng = (here/'engine.js').read_text()
(here/'index.html').write_text(src.replace('/*ENGINE*/', eng))
print('built web/index.html')
