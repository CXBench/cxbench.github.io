"""Animate original CXBench paper figures with the website's shared visual theme."""
import argparse
import asyncio
import html
import json
import math
import os
from pathlib import Path
import subprocess
import wave
from functools import lru_cache

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
OUT = ASSETS / 'video'
WORK = Path(os.environ.get('CXBENCH_VIDEO_WORK', str(ROOT / 'production/work')))
WORK.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
SCENES = json.loads((ROOT / 'production/narration.json').read_text())
DATA = json.loads((ASSETS / 'data/results.json').read_text())
THEME = json.loads((ASSETS / 'theme.json').read_text())
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SCALE = 1.5
W, H, FPS = 1920, 1080, 30
BG, INK, MUTED = (THEME[k] for k in ['background', 'ink', 'muted'])
BLUE, GREEN, RED, LINE = (THEME[k] for k in ['blue', 'green', 'red', 'line'])
SOFT, PALE_BLUE, PALE_GREEN, PALE_RED = (THEME[k] for k in ['soft', 'light_blue', 'light_green', 'light_red'])
SOURCES = ['figure1', 'figure2', 'figure3', 'figure4', 'domain_heatmap', 'rule_failure_heatmap', 'table3']
FIGURES = {name: Image.open(ASSETS / f'figures/{name}.webp').convert('RGB') for name in SOURCES}


@lru_cache(maxsize=100)
def font(size, kind='sans'):
    index = {'sans': 0, 'medium': 1, 'bold': 3, 'mono': 4}.get(kind, 0)
    path = ASSETS / ('fonts/math.ttf' if kind == 'math' else f'fonts/font-{index}.ttf')
    return ImageFont.truetype(str(path), round(size * SCALE))


def txt(draw, xy, text, size=22, fill=INK, kind='sans', anchor='la'):
    draw.text(tuple(round(v*SCALE) for v in xy), text, font=font(size, kind), fill=fill, anchor=anchor)


def line(draw, points, fill=BLUE, width=2):
    draw.line([(round(x*SCALE), round(y*SCALE)) for x,y in points], fill=fill, width=max(1,round(width*SCALE)), joint='curve')


def rect(draw, box, fill=None, outline=None, radius=0, width=1):
    box=[round(v*SCALE) for v in box]
    if radius:
        draw.rounded_rectangle(box,radius=round(radius*SCALE),fill=fill,outline=outline,width=round(width*SCALE))
    else:
        draw.rectangle(box,fill=fill,outline=outline,width=round(width*SCALE))


def circle(draw,x,y,r,fill=None,outline=None,width=2):
    draw.ellipse([round(v*SCALE) for v in (x-r,y-r,x+r,y+r)],fill=fill,outline=outline,width=round(width*SCALE))


def ease(x):
    x=max(0,min(1,x));return x*x*(3-2*x)


def appear(t,start=0,span=.16):
    return ease((t-start)/span)


def interpolate(a,b,p):
    return tuple(x+(y-x)*p for x,y in zip(a,b))


def arrow(draw,a,b,color=BLUE,p=1):
    end=interpolate(a,b,p)
    line(draw,[a,end],color,2)
    if p>.98:
        angle=math.atan2(b[1]-a[1],b[0]-a[0])
        line(draw,[(b[0]-9*math.cos(angle-.45),b[1]-9*math.sin(angle-.45)),b,(b[0]-9*math.cos(angle+.45),b[1]-9*math.sin(angle+.45))],color,2)


@lru_cache(maxsize=16)
def scaled_crop(name, crop, width, height):
    source=FIGURES[name]
    box=tuple(round(v*(source.width if i%2==0 else source.height)) for i,v in enumerate(crop))
    return source.crop(box).resize((width,height),Image.Resampling.LANCZOS)


def paper(image,name,box,crop=(0,0,1,1)):
    source=FIGURES[name]
    ratio=(source.width*(crop[2]-crop[0]))/(source.height*(crop[3]-crop[1]))
    width=min(box[2]-box[0],(box[3]-box[1])*ratio)
    height=width/ratio
    x=(box[0]+box[2]-width)/2;y=(box[1]+box[3]-height)/2
    pixels=(round(width*SCALE),round(height*SCALE))
    # Quantize the camera at sub-pixel precision while preserving smooth motion.
    crop=tuple(round(v,4) for v in crop)
    frame=scaled_crop(name,crop,*pixels)
    image.paste(frame,(round(x*SCALE),round(y*SCALE)))
    return (x,y,width,height,crop)


def map_box(placement,region):
    x,y,w,h,crop=placement
    return (x+w*(region[0]-crop[0])/(crop[2]-crop[0]),
            y+h*(region[1]-crop[1])/(crop[3]-crop[1]),
            x+w*(region[2]-crop[0])/(crop[2]-crop[0]),
            y+h*(region[3]-crop[1])/(crop[3]-crop[1]))


def outline(draw,placement,region,color,p=1):
    if p<=0:return
    x0,y0,x1,y1=map_box(placement,region)
    points=[(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]
    total=2*((x1-x0)+(y1-y0));remaining=total*p
    visible=[points[0]]
    for a,b in zip(points,points[1:]):
        length=math.dist(a,b)
        if remaining>=length:
            visible.append(b);remaining-=length
        else:
            visible.append(interpolate(a,b,remaining/length));break
    line(draw,visible,color,2.5)
    circle(draw,*visible[-1],3,color)


def source_label(draw,text,x=54,y=602):
    txt(draw,(x,y),text,10,MUTED,'mono')


def logo(draw,x,y,size=28):
    s=size/36
    rect(draw,(x+3*s,y+3*s,x+26*s,y+26*s),None,INK,5*s,1.8)
    line(draw,[(x+10*s,y+15*s),(x+15*s,y+20*s),(x+29*s,y+6*s)],INK,1.8)
    line(draw,[(x+12*s,y+32*s),(x+29*s,y+32*s),(x+33*s,y+28*s),(x+33*s,y+15*s)],INK,1.8)


BASE=Image.new('RGB',(W,H),BG)
base_draw=ImageDraw.Draw(BASE)
line(base_draw,[(48,65),(1232,65)],LINE,1)


def header(draw,scene,index):
    logo(draw,48,23,26)
    txt(draw,(84,24),'CXBench',19,INK,'bold')
    txt(draw,(1230,29),f'{index+1:02d} / 08     RESEARCH OVERVIEW',10,MUTED,'mono',anchor='ra')
    txt(draw,(52,93),scene['title'],34,INK,'medium')


def question(image,draw,t):
    pos=paper(image,'figure1',(40,163,936,580),(.05,.09,.96,.94))
    outline(draw,pos,(.17,.69,.86,.75),BLUE,appear(t,.30,.16))
    x=1084
    txt(draw,(x,214),'Two traces',24,INK,'medium',anchor='ma')
    for y,color in [(310,GREEN),(415,RED)]:
        circle(draw,985,y,6,color)
        p=appear(t,.05 if color==GREEN else .12,.22)
        arrow(draw,(996,y),(1182,y),color,p)
    txt(draw,(1080,338),'A',16,GREEN,'mono',anchor='ma')
    txt(draw,(1080,443),'B',16,RED,'mono',anchor='ma')
    if t>.34:
        txt(draw,(x,493),'Same final state',19,BLUE,'medium',anchor='ma')
    if t>.66:
        txt(draw,(x,530),'Same success?',20,INK,'medium',anchor='ma')
    source_label(draw,'FIGURE 1  /  An outcome-correct trace can still omit a required disclosure.')


def traces(image,draw,t):
    camera=interpolate((.055,.10,.96,.66),(.10,.36,.93,.94),appear(t,.59,.16))
    pos=paper(image,'figure1',(52,165,1228,565),camera)
    if t<.27:
        outline(draw,pos,(.525,.105,.955,.166),BLUE,appear(t,.04,.15))
    elif t<.59:
        outline(draw,pos,(.095,.22,.465,.35),GREEN,appear(t,.27,.08))
        outline(draw,pos,(.552,.30,.915,.365),RED,appear(t,.43,.08))
    else:
        outline(draw,pos,(.17,.69,.86,.754),BLUE,appear(t,.63,.1))
        outline(draw,pos,(.545,.88,.85,.927),GREEN,appear(t,.82,.1))
    source_label(draw,'FIGURE 1  /  Written-confirmation notice and draft confirmation are separate requirements.')


def axes(image,draw,t):
    pos=paper(image,'figure3',(615,206,1220,550),(.725,.46,.999,.96))
    txt(draw,(66,216),'O',54,BLUE,'math')
    txt(draw,(130,234),'Customer goal achieved',22,INK)
    txt(draw,(66,297),'P',54,GREEN,'math')
    txt(draw,(130,316),'Required process followed',22,INK)
    if t>.37:
        rect(draw,(55,415,557,486),PALE_GREEN,None,9)
        txt(draw,(78,431),'O ∧ P',32,GREEN,'math')
        txt(draw,(254,437),'Both-pass',23,GREEN,'medium')
    if t>.56:
        rect(draw,(55,502,557,573),PALE_RED,None,9)
        txt(draw,(78,518),'O ∧ ¬P',32,RED,'math')
        txt(draw,(254,524),'False-pass',23,RED,'medium')
        outline(draw,pos,(.807,.65,.909,.786),RED,appear(t,.56,.12))
    if t>.74:
        outline(draw,pos,(.807,.65,.996,.786),BLUE,appear(t,.74,.12))
    source_label(draw,'FIGURE 3 DETAIL  /  Outcome-only scoring accepts both outcome-pass cells.')


def grader(image,draw,t):
    pos=paper(image,'figure3',(52,184,1228,557))
    if t<.28:
        for i,region in enumerate([(.03,.055,.202,.33),(.225,.055,.397,.33),(.418,.055,.636,.33),(.657,.055,.847,.33)]):
            outline(draw,pos,region,BLUE,appear(t,.025+i*.055,.07))
    else:
        outline(draw,pos,(.202,.455,.468,.615),GREEN,appear(t,.28,.1))
        outline(draw,pos,(.202,.699,.468,.857),BLUE,appear(t,.43,.1))
        outline(draw,pos,(.504,.57,.68,.737),GREEN,appear(t,.67,.1))
    if t>.69:
        txt(draw,(640,563),'Process pass = rules pass AND judge pass',22,GREEN,'medium',anchor='ma')
    source_label(draw,'FIGURE 3  /  Source provision → rule card → trace evidence → process verdict')


def runtime(image,draw,t):
    progress=appear(t,.66,.17)
    crop=interpolate((.315,.045,.825,.47),(0,0,1,1),progress)
    pos=paper(image,'figure2',(48,178,900,585),crop)
    paper(image,'figure4',(953,208,1220,440),(.034,.025,.48,.515))
    txt(draw,(1085,180),'Task specification',15,MUTED,'medium',anchor='ma')
    line(draw,[(936,180),(936,565)],LINE,1)
    txt(draw,(968,476),'Prepare',21,BLUE,'medium')
    txt(draw,(968,510),'Confirm',21,GREEN,'medium')
    txt(draw,(968,544),'Submit',21,INK,'medium')
    if t<.29:
        outline(draw,pos,(.343,.07,.54,.195),BLUE,appear(t,.04,.1))
        outline(draw,pos,(.615,.07,.809,.195),GREEN,appear(t,.15,.1))
    elif t<.66:
        outline(draw,pos,(.345,.335,.562,.448),GREEN,appear(t,.29,.13))
    else:
        outline(draw,pos,(.003,.695,.515,.998),BLUE,appear(t,.83,.08))
    source_label(draw,'FIGURES 2 + 4  /  Runtime submission controls complement whole-trace evaluation.')


def results(image,draw,t):
    move=appear(t,.34,.13)
    box=interpolate((52,190,1228,545),(132,165,1148,429),move)
    pos=paper(image,'domain_heatmap',box)
    if t<.34:
        txt(draw,(640,563),'120 tasks  ·  6 domains  ·  7 models  =  840 executions',24,INK,'medium',anchor='ma')
    else:
        p=appear(t,.35,.22)
        for i in range(840):
            color=LINE
            if i<p*840:
                color=GREEN if i<116 else RED if i<582 else '#ced5db'
            circle(draw,57+(i%42)*10,447+(i//42)*7,2.35,color)
        for start,x,value,label,color in [(.36,630,'582','Outcome-pass',BLUE),(.47,850,'116','Both-pass',GREEN),(.65,1070,'466','False-pass',RED)]:
            if t>start:
                txt(draw,(x,458),value,51,color,'medium')
                txt(draw,(x,517),label,15,MUTED)
        if t>.77:
            txt(draw,(850,563),'466 / 582 = 80.07%',23,RED,'medium',anchor='ma')
    source_label(draw,'FIGURE 5  /  All 840 retained executions enter the headline denominator.')


def models(image,draw,t):
    pos=paper(image,'table3',(52,190,1228,520))
    if .2<t<.43:
        for y in [.325,.689]:
            outline(draw,pos,(.413,y,.478,y+.086),BLUE,appear(t,.20,.09))
    elif .43<=t<.70:
        for y in [.325,.689]:
            outline(draw,pos,(.600,y,.666,y+.086),GREEN,appear(t,.43,.08))
        if t>.53:
            outline(draw,pos,(.600,.416,.666,.502),GREEN,appear(t,.53,.1))
    elif t>=.70:
        outline(draw,pos,(.55,.04,.867,.973),GREEN,appear(t,.70,.1))
    if t<.43:
        txt(draw,(640,550),'GLM-5.1 and DeepSeek-v4-flash: 77.50% outcome-pass',22,BLUE,'medium',anchor='ma')
    elif t<.70:
        txt(draw,(640,550),'Both-pass: GLM 21.67%  ·  GPT-5.4 20.83%  ·  DeepSeek 13.33%',21,GREEN,'medium',anchor='ma')
    else:
        txt(draw,(640,550),'Descriptive differences do not establish a complete statistical ranking.',20,MUTED,anchor='ma')
    source_label(draw,'TABLE 3  /  Original manuscript table, 120 records per model; Wilson 95% intervals.')


def closing(image,draw,t):
    if t<.70:
        pos=paper(image,'rule_failure_heatmap',(45,173,840,586))
        line(draw,[(865,180),(865,584)],LINE,1)
        for start,y,value,label,color in [(.01,207,'329','Judge only',BLUE),(.13,313,'38','Rules only',GREEN),(.23,419,'99','Both',INK)]:
            if t>start:
                txt(draw,(910,y),value,48,color,'medium')
                txt(draw,(1060,y+24),label,17,MUTED)
        if t>.35:
            txt(draw,(910,514),'Encoded requirements;',17,MUTED)
            txt(draw,(910,542),'not legal certification.',17,MUTED)
        source_label(draw,'FIGURE 6  /  Rule-level failures and complementary detection among 466 false-passes.')
    else:
        logo(draw,177,210,75)
        txt(draw,(280,197),'CXBench',72,INK,'bold')
        txt(draw,(183,313),'Evaluate outcomes.',42,BLUE,'medium')
        txt(draw,(183,368),'Examine processes.',42,GREEN,'medium')
        txt(draw,(186,467),'cxbench.github.io',25,INK,'mono')
        paper(image,'figure3',(794,235,1197,499),(.725,.46,.999,.96))
        source_label(draw,'Paper, original figures, and reported results available on the project website.',186)


DRAW_SCENES=[question,traces,axes,grader,runtime,results,models,closing]


def timestamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'


async def prepare():
    semaphore=asyncio.Semaphore(3)
    async def speech(i,j,text):
        target=WORK/f'{i:02d}-{j:02d}.mp3'
        if not target.exists():
            async with semaphore:
                for attempt in range(3):
                    try:
                        await edge_tts.Communicate(text,'en-US-AndrewNeural',rate='+5%').save(str(target))
                        break
                    except Exception:
                        if target.exists():
                            target.unlink()
                        if attempt==2:
                            raise
                        await asyncio.sleep(2)
        return i,j,target
    clips=await asyncio.gather(*(speech(i,j,pair[0]) for i,s in enumerate(SCENES) for j,pair in enumerate(s['lines'])))
    clip_map={(i,j):path for i,j,path in clips}
    samples=[];timeline=[];cues=[];cursor=0.;rate=24000
    for i,scene in enumerate(SCENES):
        start=cursor
        pause=np.zeros(round(.8*rate),np.int16);samples.append(pause);cursor+=.8
        for j,(en,zh) in enumerate(scene['lines']):
            raw=subprocess.check_output([FFMPEG,'-v','error','-i',str(clip_map[(i,j)]),'-f','s16le','-ac','1','-ar',str(rate),'-'])
            pcm=np.frombuffer(raw,dtype=np.int16)
            duration=len(pcm)/rate
            cues.append({'start':cursor,'end':cursor+duration,'en':en,'zh':zh})
            samples.append(pcm);cursor+=duration
            gap=.32 if j<2 else 1.1
            samples.append(np.zeros(round(gap*rate),np.int16));cursor+=gap
        timeline.append({'start':start,'end':cursor,'id':scene['id'],'title':scene['title']})
    with wave.open(str(WORK/'narration.wav'),'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate)
        out.writeframes(np.concatenate(samples).tobytes())
    (WORK/'timeline.json').write_text(json.dumps({'duration':cursor,'scenes':timeline,'cues':cues},ensure_ascii=False,indent=2))
    print(f'Prepared narration and captions: {cursor:.2f} seconds',flush=True)

def write_text_artifacts(timing):
    for lang in ['en','zh']:
        lines=['WEBVTT','']
        for cue in timing['cues']:
            lines.extend([f'{timestamp(cue["start"])} --> {timestamp(cue["end"])}',cue[lang],''])
        (OUT/f'captions-{lang}.vtt').write_text('\n'.join(lines),encoding='utf-8')
    chapters=timing['scenes']
    (OUT/'chapters.vtt').write_text('WEBVTT\n\n'+'\n\n'.join(f'{timestamp(s["start"])} --> {timestamp(s["end"])}\n{s["title"]}' for s in chapters)+'\n')
    body=''.join(f'<section><p class="section-label">{i+1:02d} / {timestamp(chapters[i]["start"])[:8]}</p><h2>{html.escape(s["title"])}</h2>'+''.join(f'<p>{html.escape(en)}</p><p lang="zh" class="translation">{html.escape(zh)}</p>' for en,zh in s['lines'])+'</section>' for i,s in enumerate(SCENES))
    (OUT/'transcript.html').write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CXBench | Video transcript</title><link rel="stylesheet" href="../fonts/fonts.css"><link rel="stylesheet" href="../../style.css?v=2"><style>main{max-width:800px;padding:55px 24px;margin:auto}section{padding:35px 0;border-top:1px solid var(--line)}h1{font-size:42px;margin:30px 0 20px}h2{font-size:25px;margin-bottom:24px}p{font-size:15px;line-height:1.8;margin-bottom:18px}.translation{color:var(--muted);font-size:14px}.translation+p{margin-top:28px}.credits{font-size:12px;color:var(--muted)}a{color:var(--blue)}.lead{margin-bottom:40px} @media(max-width:500px){h1{font-size:32px}}</style></head><body><main><a href="../../#film">← Back to CXBench</a><h1>CXBench: a visual introduction</h1><p class="lead">Original paper figures with animated annotations. English narration and synchronized English / Chinese subtitles.</p>'''+body+'''<p class="credits">Figures 1–6 and Table 3 are from the supplied October 2026 manuscript. The video uses cropped views, zooms, and animated annotations; full original figures are available on the <a href="../../#framework">project website</a>. Narration is synthesized with the Andrew neural voice.</p></main></body></html>''',encoding='utf-8')


def make_frame(scene_index,local,absolute,duration):
    image=BASE.copy();draw=ImageDraw.Draw(image)
    header(draw,SCENES[scene_index],scene_index)
    DRAW_SCENES[scene_index](image,draw,local)
    # The lower region is reserved for native, user-selectable captions.
    rect(draw,(0,642,1280,720),BG)
    line(draw,[(52,632),(1228,632)],LINE,1)
    line(draw,[(0,717),(1280*absolute/duration,717)],GREEN,2)
    return image


def make_poster():
    image=BASE.copy();draw=ImageDraw.Draw(image)
    logo(draw,48,23,26)
    txt(draw,(84,24),'CXBench',19,INK,'bold')
    txt(draw,(1230,29),'A VISUAL INTRODUCTION  /  2:56',10,MUTED,'mono',anchor='ra')
    txt(draw,(52,195),'Correct outcome.',37,INK,'medium')
    txt(draw,(52,245),'Required process.',37,BLUE,'medium')
    txt(draw,(54,330),'A benchmark for',19,MUTED)
    txt(draw,(54,360),'process-compliant LLM agents',19,MUTED)
    pos=paper(image,'figure1',(410,133,1230,596),(.055,.09,.955,.94))
    outline(draw,pos,(.55,.30,.914,.365),RED)
    circle(draw,77,487,24,INK)
    draw.polygon([(round(x*SCALE),round(y*SCALE)) for x,y in [(72,478),(72,496),(86,487)]],fill='white')
    txt(draw,(117,476),'Explore CXBench',17,INK,'medium')
    txt(draw,(54,595),'120 tasks   ·   6 domains   ·   7 models',12,MUTED)
    line(draw,[(52,642),(1228,642)],LINE,1)
    txt(draw,(54,666),'Research overview with original paper figures',12,MUTED)
    txt(draw,(1228,666),'cxbench.github.io',12,BLUE,'mono',anchor='ra')
    image.save(OUT/'poster.jpg',quality=95)


def render(preview=False):
    timing=json.loads((WORK/'timeline.json').read_text())
    total=timing['duration'];scenes=timing['scenes']
    write_text_artifacts(timing)
    make_poster()
    contact=Image.new('RGB',(1920,1080),'white')
    for i,scene in enumerate(scenes):
        for moment in [.18,.48,.85]:
            frame=make_frame(i,moment,scene['start']+moment*(scene['end']-scene['start']),total)
            frame.save(WORK/f'scene-{i+1}-{round(moment*100)}.jpg',quality=93)
            if moment==.48:
                frame.save(WORK/f'scene-{i+1}.jpg',quality=93)
                contact.paste(frame.resize((640,360)),((i%3)*640,(i//3)*360))
    contact.save(WORK/'contact-sheet.jpg',quality=93)
    if preview:return
    command=[FFMPEG,'-y','-v','warning','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(WORK/'narration.wav'),'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-movflags','+faststart','-shortest',str(OUT/'cxbench-introduction.mp4')]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    si=0
    try:
        for n in range(math.ceil(total*FPS)):
            now=n/FPS
            while si<len(scenes)-1 and now>=scenes[si]['end']:si+=1
            scene=scenes[si];local=(now-scene['start'])/(scene['end']-scene['start'])
            image=make_frame(si,local,now,total)
            fade=min(1,(now-scene['start'])/.25,(scene['end']-now)/.25)
            if fade<1:image=Image.blend(BASE,image,max(0,fade))
            process.stdin.write(image.tobytes())
            if n%(FPS*10)==0:print(f'Rendered {now:.0f} / {total:.0f}s',flush=True)
    finally:
        process.stdin.close()
    if process.wait()!=0:raise RuntimeError('Video encoding failed')
    metadata={'duration_seconds':round(total,3),'width':W,'height':H,'fps':FPS,'narration_language':'en','subtitle_languages':['en','zh'],'chapters':scenes,'visual_theme':'../theme.json','figure_sources':[f'../figures/{name}.webp' for name in SOURCES],'visual_treatment':'Original manuscript figures, cropped details, smooth camera moves, and animated annotations.'}
    (OUT/'metadata.json').write_text(json.dumps(metadata,indent=2))
    print(f'Video ready: {OUT / "cxbench-introduction.mp4"}',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--preview',action='store_true')
    args=parser.parse_args()
    if args.prepare:
        asyncio.run(prepare())
        write_text_artifacts(json.loads((WORK/'timeline.json').read_text()))
    else:render(args.preview)
