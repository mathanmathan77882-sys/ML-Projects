from flask import Flask,request,render_template,redirect,url_for, jsonify,g , send_file
from io import BytesIO
import base64
from PIL import Image
import os
import cv2
import numpy as np
from datetime import datetime
from add_watermark_invis import add_invis,search_invis
from add_watermark import add_vis
from test2 import predict
from visible_watermark_detect import check_vis
from hidden_data_detect import hid_data
from add_visible_doc import add_vis_pdf,add_vis_doc
from template_detect import template_det
from check_doc import detect_watermark_docx,detect_watermark_pdf
from add_exif_data import add_exif
import sqlite3
from docx import Document
from docx.shared import Inches
#database connection
def connect_db():
    sql=sqlite3.connect('data.db',timeout=30)
    cur=sql.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.close()
    sql.row_factory=sqlite3.Row
    return sql 
def get_db():
    if not hasattr(g,'sqlite3' ):
        g.sqlite_db=connect_db()
    return g.sqlite_db

#def get_db_connection():
    #sql=sqlite3.connect('')
    #sql.row_factory=sqlite3.Row
    #return sql
    #conn = psycopg.connect(dbname="watermark",user="postgres",password="shive",host="localhost")
    #cur=conn.cursor()
    #return cur,conn

#def get_db():
    #if not hasattr(g,'sqlite3'):
    #    g.sqlite_db=get_db_connection()
    #return g.sqlite_db



app=Flask(__name__)


@app.teardown_appcontext
def close_db(error):
    if hasattr(g,'sqlite_db'):
        g.sqlite_db.close()
#index
@app.route('/',methods=['post','get'])
def index():
    return redirect(url_for('login'))

#login page
@app.route('/login',methods=['post','get'])
def login():
    if request.method=='POST':
        username=request.form.get('username')
        passwd=request.form.get('password')
        cur=get_db()
        data=cur.execute('Select password from users where username=?',(username,))
        try:
            data=data.fetchone()
            data1=data['password']
        except:
            return redirect(url_for('login'))
        cur.close()
       
        if data['password']==passwd:
            return redirect(url_for('all',username=username))
        else:
            return redirect(url_for('login'))
        
    return render_template('login.html')

#signup page
@app.route('/signup',methods=['post','get'])
def signup():
    if request.method=='POST':
   
        username=request.form.get('username')
        passwd=request.form.get('password')

        cur=get_db()
        try:
            data=cur.execute('select * from users where username=(?)',(username,)).fetchall()
        except:
            data=None
        if data:
            cur.close()
            
            return 'ALREADY EXISTS'
        else:
            cur.execute('insert into users(username,password) values((?),(?))',(username,passwd))
            cur.commit()
            cur.close()
           
        return redirect(url_for('login'))
    return render_template('signup.html')


#after login/signup home page
@app.route('/all/')
@app.route('/all/<username>',methods=['post','get'])
def all(username='guest'):
    if request.method=='POST':
        dic={}
        now=datetime.now()
        
        date=now.strftime("%A, %B %d, %Y %H:%M:%S")
        img_og=request.files['image']
        nparr = np.frombuffer(img_og.read(), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        output=predict(img)
        if output > 0.5:
            dic['watermark']=f"LIKELY WATERMARK PRESENT WITH {output*100-20} % CONFIDENCE"
        else:
            dic['watermark']=f"NO WATERMARK DETECTED WITH {output*100} % CONFIDENCE"
        op2,output2=check_vis(img)
        dic['visible watermark clear']=op2
        dic['visible but uneligible']=output2
        op3,output3=hid_data(img)
        dic['exif_data']=output3
        dic['hidden cip file']=op3
        img_og.seek(0)
        img_bytes = img_og.read()
        if username!='guest':
            typ='.png'
            cur=get_db()
            d=cur.execute('select id from users where username=(?)',(username,)).fetchone()
            user=d['id']
            cur.execute("insert into datas(id,image,query,type,created_at) values((?),(?),(?),?,?)",(user,sqlite3.Binary(img_bytes),str(dic),typ,date))
            cur.commit()
            cur.close()
            
        print('hello')
        return jsonify(dic)
    return render_template('home.html',username=username)

#template detection 
@app.route('/template/')
@app.route('/template/<username>',methods=['post','get'])
def temp(username='guest'):
    if request.method=='POST':
        img1=request.files['template_image']
        img2=request.files.getlist('main_image')
        dic={}
        img_bytes=None
        now=datetime.now()
        
        date=now.strftime("%A, %B %d, %Y %H:%M:%S")
        for i in img2:
            dic[i.filename]=template_det(i,img1)
            i.seek(0)
            img_bytes=i.read()
        if username!='guest':
            typ='.png'
            cur=get_db()
            d=cur.execute('select id from users where username=(?)',(username,)).fetchone()
            user=d['id']
            cur.execute("insert into datas(id,image,query,type,created_at) values((?),(?),(?),?,?)",(user,sqlite3.Binary(img_bytes),str(dic),typ,date))
            cur.commit()
            cur.close()

        return jsonify(dic)
    return render_template('template.html',username=username)

#redirect from home page to add visible tag
#WARNING visible watermarks cannot be removed
@app.route('/add/')
@app.route('/add/<username>',methods=['post','get'])
def add(username='guest'):
    options={'opacity':['bold','transparent','invisible'],'position':['center','center-right','center-left','center-bottom','center-top'],'font':['BROADW.TTF','ARLRDBD.TTF','BASKVILL.TTF','CASTELAR.TTF','CENTURY.TTF']}
    if request.method=='POST':
        smth=request.files.get('image')
        print(type(smth))
        now=datetime.now()
        
        date=now.strftime("%A, %B %d, %Y %H:%M:%S")
        
        print(date)
        if smth.filename.lower().endswith('.pdf'):
            img=request.files['image']
           
            text=request.form.get('text')
            font=request.form.get('font')
            opacity=request.form.get('opacity')
            size=request.form.get('size')
            image=add_vis_pdf(img,text,font,opacity,size)
            
        elif smth.filename.lower().endswith('.doc') or smth.filename.lower().endswith('.docx'):
            img=request.files['image']
            text=request.form.get('text')
            font=request.form.get('font')
            opacity=request.form.get('opacity')
            size=request.form.get('size')
            image=add_vis_doc(img,text,font,opacity,size)
        else:
            img=request.files['image']
            text=request.form.get('text')
            position=request.form.get('position')
            font=request.form.get('font')
            opacity=request.form.get('opacity')
            size=request.form.get('size')
            image=add_vis(img,text,position,font,opacity,size)
            image=add_exif(image,date)
        if username!='guest':
            typ=None
            cur=get_db()
            img_bytes=None
            if smth.filename.lower().endswith('.pdf'):
                typ='.pdf'
                img_bytes = image.read()
                
            elif smth.filename.lower().endswith('.doc') or smth.filename.lower().endswith('.docx'):
                typ='.docx'
                img_bytes=image.read()
            else:
                _, buffer = cv2.imencode(".png", image)
                img_bytes = buffer
                typ='.png'
            d=cur.execute('select id from users where username=?',(username,)).fetchone()
            user=d['id']
            cur.execute('insert into datas(id,image,added_watermark,type,created_at) values((?),(?),(?),?,?)',(user,sqlite3.Binary(img_bytes),text,typ,date))
            cur.commit()
            cur.close()
            
        buf = BytesIO()
        if smth.filename.lower().endswith('.pdf'):
            image.seek(0)
            
            return send_file(
            image,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="file.pdf"
            )
        elif smth.filename.lower().endswith('.doc') or smth.filename.lower().endswith('.docx'):
            image.seek(0)
            
            doc_obj = Document(image)
            buf = BytesIO()
            doc_obj.save(buf)
            buf.seek(0)

            return send_file(
                buf,
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                as_attachment=True,
                download_name="file.docx"
            )
        else:
            
            image=cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
            image=Image.fromarray(image)
            image.save(buf, format="PNG")
            buf.seek(0)
            return send_file(buf,mimetype='image/png',as_attachment=True,download_name='image.png')
        
    return render_template('add.html',options=options,username=username)

#WARNING invisible watermarks cannot be removed
@app.route('/addinvis/')
@app.route('/addinvis/<username>',methods=['post','get'])
def addinvis(username='guest'):
    if request.method=='POST':
        now=datetime.now()
        
        date=now.strftime("%A, %B %d, %Y %H:%M:%S")
        img=request.files['image']
        security_key=request.form.get('key')
        img=add_invis(img,security_key)
        if username!='guest':
            typ='.png'
            cur=get_db()
            _, buffer = cv2.imencode(".jpg", img)
            img_bytes = buffer.tobytes()
            d=cur.execute('select id from users where username=(?)',(username,)).fetchone()
            user=d['id']

            cur.execute('insert into datas(id,image,added_watermark,type,created_at) values((?),(?),(?),?,?)',(user,sqlite3.Binary(img_bytes),security_key,typ,date))
            cur.commit()
            cur.close()
           
        buf = BytesIO()
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        pil = Image.fromarray(img_rgb)
        pil.save(buf, format="JPEG")
        
        buf.seek(0)
        return send_file(buf,mimetype='image/png',as_attachment=True,download_name='image.png')
    return render_template('addinvis.html',username=username)

#search invisible data using the security key 
@app.route('/searchinvis/')
@app.route('/searchinvis/<username>',methods=['post','get'])
def searchinvis(username='guest'):
    if request.method=='POST':
        now=datetime.now()
        
        date=now.strftime("%A, %B %d, %Y %H:%M:%S")
        img=request.files['image']
        security_key=request.form.get('key')
        img=search_invis(img,security_key)
        if username!='guest':
            typ='.png'
            cur=get_db()
            _, buffer = cv2.imencode(".jpg", img)
            img_bytes = buffer.tobytes()
            d=cur.execute('select id from users where username=(?)',(username,)).fetchone()
            user=d['id']
            cur.execute('insert into datas(id,image,query,type,created_at) values(?,(?),(?),?,?)',(user,sqlite3.Binary(img_bytes),security_key,typ,date))
            cur.commit()
            cur.close()
            
        buf = BytesIO()
        img.save(buf, format="JPEG")
        img_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        buf.seek(0)
        return render_template('searchinvis.html',image_data=img_base64)
    return render_template('searchinvis.html')



#based on userid display history
@app.route('/history/')
@app.route('/history/<username>')
def history(username='guest'):
    if request.method=='POST':
        month=None
        day=None
        if request.method=='POST':
            month = request.args.get("month").zfill(2)
            day = request.args.get("day").zfill(2)
        
        cur=get_db()
        try:
            data=cur.execute('select * from users where username=(?)',(username,)).fetchone()
        except:
            data=None
        if data:
            if month and day:
                data=cur.execute('select * from datas join users on datas.id=users.id where users.username=(?) and strftime("%m-%d",created_at)=?',(username,f"{month}-{day}")).fetchall()
                data2=cur.execute('select * from documents join users on documents.id where users.username=(?) and strftime("%m-%d",created_at)=?',(username,f"{month}-{day}")).fetchall()

            else:
                data=cur.execute('select * from datas join users on datas.id=users.id where users.username=(?)',(username,)).fetchall()
                data2=cur.execute('select * from documents join users on documents.id where users.username=(?)',(username,)).fetchall()

            cur.close()
           
        else:
            return redirect(url_for('login'))
    return render_template('history.html',username=username)

#documents and pdf option
@app.route('/docorpdf/')   
@app.route('/docorpdf/<username>',methods=['POST','GET'])
def docorpdf(username='guest'):

    if request.method=='POST':
        
        pdf=request.files['file']
        word=request.form.get('word')
        cur=get_db()
        now=datetime.now()
        
        date=now.strftime("%A, %B %d, %Y %H:%M:%S")
       
        if pdf.filename.lower().endswith(".pdf"):
            print('hello')
            typ='.pdf'
            dic1,dic2,dic3=detect_watermark_pdf(pdf,word)
            d=cur.execute('select id from users where username=(?)',(username,)).fetchone()
            user=d['id']
            cur.execute('insert into datas(id,image,query,type,created_at) values(?,?,?,?,?)',(user,sqlite3.Binary(pdf.read()),str([dic1,dic2,dic3]),typ,date))
            cur.commit()
            cur.close()
            return jsonify({'output':[dic1,dic2,dic3]})
        elif pdf.filename.lower().endswith(".docx") or pdf.filename.lower().endswith(".doc"):
            typ='.docx'
            if pdf.filename.lower().endswith(".doc"):
                return 'please upload a .docx file'
            dic1,dic2=detect_watermark_docx(pdf,word)
            d=cur.execute('select id from users where username=?',(username,)).fetchone()
            user=d['id']
            cur.execute('insert into datas(id,image,query,type,created_at) values(?,?,?,?,?)',(user,sqlite3.Binary(pdf.read()),str([dic1,dic2]),typ,date))
            cur.commit()
            cur.close()
            return jsonify({'output':[dic1,dic2]})
        
    return render_template('updoc.html',username=username)

#api calls for user history
@app.route("/api/hist/<username>", methods=["GET"])
def hist(username):
    conn = get_db()
    cur = conn.cursor()
    id=cur.execute('select id from users where username=?',(username,)).fetchone()
    id=id['id']
    cur.execute("SELECT * FROM datas where id=? ORDER BY created_at DESC ",(id,))
    rows = cur.fetchall()
    conn.close()
    data = []
    for r in rows:
      
        item = {
            "id": r["id2"],
            "type": r["type"],
            "created_at": r["created_at"],
            "query": r["query"],
            'added_watermark':r['added_watermark']
        }
        if r["type"] == ".png":
            item["image"] = base64.b64encode(r['image']).decode("utf-8")
            item["preview_url"] = f"/api/preview/{r['id2']}"
        if r["type"] == ".pdf" or r['type']=='.docx':
            item["image"] = base64.b64encode(r['image']).decode("utf-8")
        data.append(item)
    
    return jsonify(data)

#api call for user history image preview
@app.route("/api/preview/<int:id>")
def preview_image(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT image,id2 FROM datas WHERE id2=?", (id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return "Not found", 404
    print(row['id2'])
    return send_file(
        BytesIO(row["image"]),
        mimetype="image/png"
    )

        
        
if __name__=='__main__':
    app.run(debug=True)

