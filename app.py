import os
from os.path import join, dirname
from dotenv import load_dotenv
import uuid
from pymongo import MongoClient
import jwt #pip install pyjwt 
from datetime import datetime, timedelta 
import hashlib #untuk enkripsi, sudah bawaan
from flask import (
    Flask, 
    render_template, 
    jsonify, 
    request,
    redirect, 
    url_for )
from werkzeug.utils import secure_filename
from bson import ObjectId



dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")
SECRET_KEY = os.environ.get("SECRET_KEY")
TOKEN_KEY = os.environ.get("TOKEN_KEY")

client = MongoClient(MONGODB_URI)

db = client[DB_NAME]

app = Flask(__name__)

# app.config['TEMPLATES_AUTO_RELOAD']=True
app.config['UPLOAD_FOLDER']='./static/gunung_pics'

@app.route('/', methods=['GET']) #UNTUK HALAMAN INDEX
def home():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.users.find_one({'useremail' :payload.get('useremail')})
        user_role = user_info['role']
        return render_template('index.html', user_role = user_role)
    except jwt.ExpiredSignatureError:
        msg = 'Your token has expired'
        return redirect(url_for('halaman_login',msg = msg))
    except jwt.exceptions.DecodeError:
        msg = 'There was a problem logging you in'
        return redirect(url_for('halaman_login',msg = msg))

@app.route('/halaman_login', methods=['GET']) #UNTUK HALAMAN LOGIN
def halaman_login():
    msg = request.args.get('msg')
    return render_template('login.html', msg =msg)
    
@app.route("/sign_in", methods=["POST"])  # UNTUK HALAMAN LOGIN
def sign_in():
    useremail_receive = request.form["useremail_give"]
    password_receive = request.form["password_give"]
    
    # Check if the email is registered
    user = db.users.find_one({"useremail": useremail_receive})
    
    if user is None:
        return jsonify({
            "result": "fail",
            "msg": "Email belum terdaftar. Silakan daftar akun terlebih dahulu."
        })

    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.users.find_one({
        "useremail": useremail_receive,
        "password": pw_hash,
    })

    if result:
        payload = {
            "useremail": useremail_receive,
            # the token will be valid for 24 hours
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify({
            "result": "success",
            "token": token,
        })
    else:
        return jsonify({
            "result": "fail",
            "msg": "Email atau Password anda tidak sesuai",
        })

@app.route('/halaman_signup', methods=['GET']) #UNTUK HALAMAN SIGNUP
def halaman_signup():
    return render_template('signup.html')

@app.route("/sign_up/save", methods=["POST"]) #UNTUK HALAMAN SIGNUP
def sign_up():
    useremail_receive = request.form['useremail_give']
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "useremail" : useremail_receive,
        "username"  : username_receive,
        "password"  : password_hash,
        "role"      : "user"
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route('/sign_up/check_email', methods=['POST'])  #UNTUK HALAMAN SIGNUP
def check_dup():
    useremail_receive = request.form['useremail_give']
    exists = bool(db.users.find_one({"useremail": useremail_receive}))
    return jsonify({'result': 'success', 'exists': exists})


@app.route('/halaman_tambah', methods=['GET']) #UNTUK HALAMAN TAMBAH
def halaman_tambah():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        return render_template('tambah.html')
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route('/tambah_gunung', methods=['POST']) #UNTUK HALAMAN TAMBAH
def posting():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        #di browser client, buat kondisi input tidak boleh kosong, termasuk input choose file
        name_receive = request.form.get('name_give')
        provinsi_receive = request.form.get('provinsi_give')
        ketinggian_receive = request.form.get('ketinggian_give')
        gmaps_receive = request.form.get('gmaps_give')
        iframe_receive = request.form.get('iframe_give')
        deskripsiUmum_receive = request.form.get('deskripsiUmum_give')
        deskripsiPerlengkapan_receive = request.form.get('deskripsiPerlengkapan_give')
        deskripsiPeringatan_receive = request.form.get('deskripsiPeringatan_give')

        if 'file_give' in request.files:
            file = request.files.get('file_give')
            file_name = secure_filename(file.filename)
            picture_name= file_name.split(".")[0]
            ekstensi = file_name.split(".")[1]
            picture_name = f"{picture_name}[{name_receive}].{ekstensi}"
            file_path = f'./static/gunung_pics/{picture_name}'
            file.save(file_path)
        else: picture_name =f"default.jpg"

        doc = {
            'nama_gunung' : name_receive,
            'provinsi_gunung' : provinsi_receive,
            'ketinggian_gunung' : ketinggian_receive,
            'gambar_gunung' : picture_name,
            'link_gmaps' : gmaps_receive,
            'link_iframe' : iframe_receive,
            'deskripsi_umum' : deskripsiUmum_receive,
            'deskripsi_perlengkapan' : deskripsiPerlengkapan_receive,
            'deskripsi_peringatan' : deskripsiPeringatan_receive,
        }
        db.gunung.insert_one(doc)
        return jsonify({
            'result' : 'success',
            'msg' : 'Konten baru telah ditambahkan!'
        })
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))
        
@app.route('/getListGunung', methods=['GET'])  # UNTUK HALAMAN INDEX DAN SEARCH DI GAGAL CARI
def get_gunung():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.users.find_one({'useremail': payload.get('useremail')})
        
        kategori = request.args.get('kategori', 'default')
        save = request.args.get('save', 'default')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 6, type=int)

        list_gunung = []

        if kategori == 'default' and save == 'default':
            list_gunung = list(db.gunung.find({}))
        elif kategori == 'favorit' or save == 'bookmark':
            list_gunung = list(db.gunung.find({}))
            for gunung in list_gunung:
                gunung['_id'] = str(gunung['_id'])
                gunung['likes'] = db.likes.count_documents({
                    'id_gunung': gunung['_id']
                })
                gunung['saves'] = db.saves.count_documents({
                    'id_gunung': gunung['_id']
                })

            if kategori == 'favorit':
                list_gunung = sorted(list_gunung, key=lambda x: x['likes'], reverse=True)
                list_gunung = [gunung for gunung in list_gunung if gunung['likes'] != 0]
            if save == 'bookmark':
                saved_gunung_ids = set(save['id_gunung'] for save in db.saves.find({'useremail': user_info.get('useremail')}))
                list_gunung = [gunung for gunung in list_gunung if gunung['_id'] in saved_gunung_ids]
                list_gunung = sorted(list_gunung, key=lambda x: x['saves'], reverse=True)
                list_gunung = [gunung for gunung in list_gunung if gunung['saves'] != 0]

            if not list_gunung:
                return jsonify({'result': 'list_kosong'})
        else:
            keyword = kategori if kategori != 'default' else save
            list_gunung = list(db.gunung.find({'$or': [
                {'nama_gunung': {'$regex': keyword, '$options': 'i'}},
                {'provinsi_gunung': {'$regex': keyword, '$options': 'i'}}
            ]}))
            if not list_gunung:
                return jsonify({'result': 'gagal_cari'})
        
        total = len(list_gunung)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_gunung = list_gunung[start:end]
        
        for gunung in paginated_gunung:
            gunung['_id'] = str(gunung['_id'])
            gunung['likes'] = db.likes.count_documents({
                'id_gunung': gunung['_id']
            })
            gunung['saves'] = db.saves.count_documents({
                'id_gunung': gunung['_id']
            })
        
        return jsonify({
            'result': 'success',
            'list_gunung': paginated_gunung,
            'total': total,
            'page': page,
            'per_page': per_page
        })

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))


@app.route('/halaman_gagal', methods=['GET'])
def gagal_cari():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        return render_template('gagal_cari.html')
        
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))
    
@app.route('/search', methods=['GET'])
def search():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        keyword = request.args.get('keyword')
        user_info = db.users.find_one({'useremail' :payload.get('useremail')})
        user_role = user_info['role']
        return render_template('index.html', user_role = user_role, keyword = keyword)
        
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route('/halaman_edit/<id_gunung>', methods=['GET']) #UNTUK HALAMAN EDIT, id gunung dibawa dengan dinamic route
def halaman_edit(id_gunung):
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        id_gunung = ObjectId(id_gunung)
        info_gunung = db.gunung.find_one({'_id' : id_gunung})
        info_gunung["_id"] = str(info_gunung["_id"])
        return render_template('edit.html', info_gunung=info_gunung)
    
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route('/edit_gunung', methods=['POST'])  #UNTUK HALAMAN EDIT
def edit():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        id_gunung = request.form.get('id_gunung_give')
        id_gunung = ObjectId(id_gunung)

        name_receive = request.form.get('name_give')
        provinsi_receive = request.form.get('provinsi_give')
        ketinggian_receive = request.form.get('ketinggian_give')
        gmaps_receive = request.form.get('gmaps_give')
        iframe_receive = request.form.get('iframe_give')
        deskripsiUmum_receive = request.form.get('deskripsiUmum_give')
        deskripsiPerlengkapan_receive = request.form.get('deskripsiPerlengkapan_give')
        deskripsiPeringatan_receive = request.form.get('deskripsiPeringatan_give')

        if 'file_give' in request.files:
            data_lama = db.gunung.find_one({'_id' : id_gunung})
            gambar_lama = data_lama['gambar_gunung']
            if gambar_lama != "default.jpg" :
                os.remove(f'./static/gunung_pics/{gambar_lama}') #hapus gambar lama di server biar ga jadi sampah

            file = request.files.get('file_give')
            file_name = secure_filename(file.filename)
            picture_name= file_name.split(".")[0]
            ekstensi = file_name.split(".")[1]
            picture_name = f"{picture_name}[{name_receive}].{ekstensi}"
            file_path = f'./static/gunung_pics/{picture_name}'
            file.save(file_path)

            doc = {
                'nama_gunung' : name_receive,
                'provinsi_gunung' : provinsi_receive,
                'ketinggian_gunung' : ketinggian_receive,
                'gambar_gunung' : picture_name,
                'link_gmaps' : gmaps_receive,
                'link_iframe' : iframe_receive,
                'deskripsi_umum' : deskripsiUmum_receive,
                'deskripsi_perlengkapan' : deskripsiPerlengkapan_receive,
                'deskripsi_peringatan' : deskripsiPeringatan_receive,
            }

        else :
            doc = {
                'nama_gunung' : name_receive,
                'provinsi_gunung' : provinsi_receive,
                'ketinggian_gunung' : ketinggian_receive,
                'link_gmaps' : gmaps_receive,
                'link_iframe' : iframe_receive,
                'deskripsi_umum' : deskripsiUmum_receive,
                'deskripsi_perlengkapan' : deskripsiPerlengkapan_receive,
                'deskripsi_peringatan' : deskripsiPeringatan_receive,
            }
        db.gunung.update_one({'_id' : id_gunung},{'$set': doc})
        return jsonify({
            'result' : 'success',
            'msg' : 'Data berhasil diedit'
        })
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))
    
@app.route('/delete_gunung', methods=['POST'])  #UNTUK HALAMAN DELETE
def delete_gunung():
    token_receive = request.cookies.get(TOKEN_KEY)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )

        id_gunung = request.form.get('id_gunung_give')
        id_gunung = ObjectId(id_gunung)
        info_gunung = db.gunung.find_one({'_id' : id_gunung})
        gambar_gunung = info_gunung['gambar_gunung']
        if gambar_gunung != "default.jpg":
            os.remove(f'./static/gunung_pics/{gambar_gunung}') #hapus gambar lama di server biar ga jadi sampah
        db.gunung.delete_one({'_id' : id_gunung})
        id_gunung = str(id_gunung)  #hapus likes dan komen pada gunungnya juga di database
        db.likes.delete_many({'id_gunung': id_gunung})
        db.komentar.delete_many({'id_gunung': id_gunung})
        db.jalur_pendakian.delete_many({'id_gunung': id_gunung})
        db.ratings.delete_many({'id_gunung': id_gunung})
        db.saves.delete_many({'id_gunung': id_gunung})
        # db.jalur.delete_many({'id_gunung': id_gunung})
        return jsonify({ 'result' : 'success' , 'msg' : 'Data gunung berhasil dihapus'})

    except(jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))


@app.route('/detail/<id_gunung>', methods=['GET']) #UNTUK HALAMAN DETAIL, id gunung dibawa dengan dinamic route
def detail_gunung(id_gunung):
    token_receive = request.cookies.get(TOKEN_KEY)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.users.find_one({'useremail' : payload.get('useremail')})
        user_role = user_info['role']
        id_gunung = ObjectId(id_gunung)
        info_gunung = db.gunung.find_one({'_id' : id_gunung})
        id_gunung = str(id_gunung)
        komentar_gunung = list(db.komentar.find({'id_gunung' : id_gunung}).sort('tanggal', -1).limit(10))
        for komentar in komentar_gunung:
            komentar['tanggal'] = komentar['tanggal'].split('-')[0]
        jumlah_komentar = len(komentar_gunung)
        # rating_gunung = list(db.ratings.find({'id_gunung': id_gunung}))

        rating_gunung = list(db.ratings.find({'id_gunung': id_gunung}).sort('tanggal', -1).limit(10))
        for rating in rating_gunung:
            rating['tanggal'] = rating['tanggal'].split('-')[0]
        jumlah_rating = len(rating_gunung)  

        like =bool(db.likes.find_one({
            'id_gunung' : id_gunung,
            'useremail' : payload.get('useremail')            
        }))
        like= str(like)

        save =bool(db.saves.find_one({
            'id_gunung' : id_gunung,
            'useremail' : payload.get('useremail')            
        }))
        save= str(save)

        jalur_pendaki = db.jalur_pendakian.find({"id_gunung":id_gunung})

        output = []

        for i in jalur_pendaki:
            output.append(i)
        return render_template('detail.html',
                    user_role = user_role,
                                jalur_pendaki=output, 
                               info_gunung=info_gunung, 
                               komentar_gunung=komentar_gunung, 
                               jumlah_komentar=jumlah_komentar,
                               rating_gunung=rating_gunung,
                               jumlah_rating = jumlah_rating,
                               like=like,
                               save=save)

    except(jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route('/komentar', methods=['POST'])  #UNTUK HALAMAN DETAIL
def tambah_komentar():
    token_receive = request.cookies.get(TOKEN_KEY)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.users.find_one({'useremail' : payload.get('useremail')})

        id_gunung = request.form.get('id_gunung_give')
        useremail = user_info['useremail']
        username = user_info['username']
        komentar_receive = request.form.get('komentar_give')

        theId = f"{uuid.uuid1()}"
        doc = {
            "uuid": theId,
            'id_gunung' : id_gunung,
            'useremail' : useremail,
            'username' : username,
            'komentar': komentar_receive,
            'tanggal' : datetime.now().strftime('%d/%m/%Y-%H:%M:%S')
        }
        db.komentar.insert_one(doc)
        return jsonify({ 'result' : 'success' , 'msg' : 'Berhasil menambahkan komentar'})

    except(jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))
        
@app.route('/hapus_komentar', methods=['POST'])  #UNTUK DELETE KOMENTAR
def delete_komentar():

    id_receive = request.form.get('id_give')  
    db.komentar.delete_one({'uuid' : id_receive})
    return jsonify({ 'result' : 'success' , 'msg' : f'Komentar berhasil dihapus'})

@app.route('/update_like', methods=['POST'])   #UNTUK HALAMAN DETAIL
def update_like():
    token_receive = request.cookies.get(TOKEN_KEY)
    try: 
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.users.find_one({'useremail' : payload.get('useremail')})
        id_gunung = request.form.get('id_gunung_give')
        action_receive = request.form.get('action_give')
        doc = {
            'id_gunung' : id_gunung,
            'useremail' : user_info.get('useremail')
        }
        if action_receive == 'like' :
            db.likes.insert_one(doc)
        else : db.likes.delete_one(doc)

        return jsonify({
            'result' : 'success',
            'msg' : 'Updated!',
        })
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route('/update_save', methods=['POST'])   #UNTUK HALAMAN DETAIL
def update_save():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.users.find_one({'useremail' : payload.get('useremail')})
        id_gunung = request.form.get('id_gunung_give')
        action_receive = request.form.get('action_give')
        doc = {
            'id_gunung' : id_gunung,
            'useremail' : user_info.get('useremail')
        }
        if action_receive == 'save' :
            db.saves.insert_one(doc)
        else : db.saves.delete_one(doc)

        return jsonify({
            'result' : 'success',
            'msg' : 'Updated!',
        })
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route('/rating', methods=['POST'])  #UNTUK HALAMAN DETAIL
def tambah_rating():
    token_receive = request.cookies.get(TOKEN_KEY)

    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.users.find_one({'useremail' : payload.get('useremail')})

        id_gunung = request.form.get('id_gunung_give')
        useremail = user_info['useremail']
        username = user_info['username']
        rating_receive = request.form.get('rating_give')

        theId = f"{uuid.uuid1()}"
        doc = {
            "uuid": theId,
            'id_gunung' : id_gunung,
            'useremail' : useremail,
            'username' : username,
            'rating': rating_receive,
            'tanggal' : datetime.now().strftime('%d/%m/%Y-%H:%M:%S')
        }
        db.ratings.insert_one(doc)
        return jsonify({ 'result' : 'success' , 'msg' : 'Berhasil menambahkan komentar'})

    except(jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route("/tambah_jalur/<id_gunung>", methods=['POST'])
def tambah_jalur(id_gunung):
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        jalur_receive = request.form["jalur"]
        kesulitan_receive = request.form["kesulitan"]
        estimasi_receive = request.form["estimasi"]
    # taro validasi
        theId = f"{uuid.uuid1()}"
        doc = {
            "uuid": theId,
            "id_gunung": id_gunung,
            "jalur": jalur_receive,
            "kesulitan": kesulitan_receive,
            "estimasi": estimasi_receive,            
        }
        db.jalur_pendakian.insert_one(doc)
        return redirect(f"/detail/{id_gunung}")
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("detail_gunung", msg="Gagal Berhasil"))

@app.route("/edit-jalur/<uuid>", methods=["POST"])
def edit_jalur(uuid):
    datanya = db.jalur_pendakian.find_one({"uuid": uuid})    
    new_doc = {   
        "uuid": uuid,   
        "id_gunung": datanya.get('id_gunung'),    
        "jalur": request.form["jalur"],
        "kesulitan": request.form["kesulitan"],
        "estimasi": request.form["estimasi"],            
    }
    
    db.jalur_pendakian.update_one({"uuid": uuid}, {"$set": new_doc})
    return redirect(f"/detail/{datanya.get('id_gunung')}")

@app.route('/hapus_jalur', methods=['POST'])  #UNTUK HALAMAN DELETE Pendaki
def delete_jalur():
    id_receive = request.form.get('id_give')  
    db.jalur_pendakian.delete_one({'uuid' : id_receive})
    return jsonify({ 'result' : 'success' , 'msg' : f'Data Jalur Pendaki berhasil dihapus'})



def replace_characters(text):
    text = text.replace('\n', '\\n')
    
    text = text.replace('\r', '\\r')

    text = text.replace('\t', '\\t')

    return text

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)