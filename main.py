import datetime

import werkzeug
from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditor, CKEditorField
from datetime import date
from flask import abort,flash
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK-KEY")
Bootstrap5(app)

#<img src="{{ avatars.gravatar(hashlib.md5(n.user.email.lower().encode('utf-8')).hexdigest()) }}">

# CREATE DATABASE
class Base(DeclarativeBase):
    pass
#, "sqlite:///posts8.db"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI")
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# CREATE FORM

app.config['CKEDITOR_PKG_TYPE'] = 'basic'
ckeditor = CKEditor(app)

class Form(FlaskForm):
    title=StringField(label="Blog Post title", validators=[DataRequired()])
    subtitle=StringField(label="Subtitle", validators=[DataRequired()])
    name=StringField(label="Your name", validators=[DataRequired()])
    image=StringField(label="Blog Image url", validators=[DataRequired()])
    text=CKEditorField(label="Your Text", validators=[DataRequired()])
    submit=SubmitField(label="Public")

class FormComment(FlaskForm):
    text=CKEditorField(label="Your Comment", validators=[DataRequired()])
    submit=SubmitField(label="Public")

# CREO TABELLA USER E POST

class User(UserMixin,db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(250), nullable=False)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    posts_figli: Mapped["BlogPost"]= db.relationship(backref="user")
    comments_figli: Mapped["Comment"]= db.relationship(backref="user")
   #collego lo user ai suoi post
   #ATTENZIONE: NON CHIAMARE I BACKREF ALLO STESSO MODO DEGLI ATTRIBUTI (AGGIUNGICI ALLA FINE LA PAROLA FIGLIO O
   #GENITORE)

class BlogPost(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(250), nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id")) #la chiave ce l'anno solo gli oggetti delle classi che vengono associati
    #le variabili "dipendenti". Tu non associ uno user ai suoi post quando ne crei uno nuovo, perché ovviamente non ha
    #ancora creato nessun post (lo user é la variabile indipendente, non ha bisogno di nessuna ForeignKey)
    #al contrario usi la ForeignKey per i posts, perché ogni volta che crei un nuovo post devi specificare
    #fra is uoi attributi anche l'attributo user_id (cioé l'id dello user che l'ha creato. E attraverso la foreign
    #Key questo user.id verrá associato alla tabella degli users.
    user_genitore: Mapped["User"] = db.relationship(backref="posts") #collego i post allo user_id
    comments_figli: Mapped["Comment"]= db.relationship(backref="posts")

class Comment(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comment: Mapped[str] = mapped_column(String(250), unique=False, nullable=False)
    user_genitore: Mapped["User"] = db.relationship(backref="comments")
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    blog_post_genitore: Mapped["BlogPost"] = db.relationship(backref="comments")
    blog_post_id_genitore: Mapped[int] = mapped_column(ForeignKey("blog_post.id"))


#crea tabelle per tutti i bind del motore
with app.app_context():
    db.create_all()

#CREO LOGIN MANAGER
log_manag= LoginManager()

#collego il manager alla mia app
log_manag.init_app(app)


#---------------------------------------------- PAGINA PRINCIPALE ----------------------------------------------------
#l'oggetto corrisponde all'utente loggato attualmente
oggetto=""


@app.route('/')
def get_all_posts():
    global oggetto
    try:
     login_user(oggetto)
     id=oggetto.id
    except:
        id=None

    oggetti=db.session.query(BlogPost)

    return render_template("index.html", all_posts=oggetti, id_persona=id)

#--------------------------------------------- AGGIUNGO UTENTI ------------------------------------------------------

def admin_only(funzione):
    def wrapper(*args,**kwargs):
        try:
            global oggetto
            login_user(oggetto)
            id=oggetto.id
            if id==1 or id=="1":
                return funzione(*args,**kwargs)

            else:
                print(f"L'oggetto non é 1: {oggetto.id}")
                return "<h1> Forbidden! </h1>" \
                       "<p> You don't have permission to access this content </p>"

        except:
            print(f"L'oggetto non é 1: {oggetto.id}")
            return "<h1> Forbidden! </h1>" \
                       "<p> You don't have permission to access this content </p>"
    wrapper.__name__ = funzione.__name__
    return wrapper

@log_manag.user_loader
def load_user(oggetto_id):
    oggetto=db.session.execute(db.select(User).where(User.id==oggetto_id)).scalar()
    return oggetto

@app.route('/register', methods=["GET","POST"])
def register():
    if request.method=="POST":

        #NOTA: il form é come un dizionario in cui le keys sono i name del form
        #quindi puoi ottenere i values delle keys o 1) come se stessi accedendo ad un dizionario
        #oppure 2) con il metodo request.form.get(nome della key) >request=funzione di Flask. get=metodo di form
        name= request.form["name"]
        email=request.form["email"]

        #controllo se la mail non esista giá nel database
        oggetto_mail=db.session.execute(db.select(User).where(User.email==email)).scalar()
        if oggetto_mail:
            flash("Email already exists. Please login", "error")
            return render_template("login.html")

        password=request.form["password"]
        password_hashata=werkzeug.security.generate_password_hash(password, method="pbkdf2",salt_length=8)

        #aggiungo il nuovo utente al SECONDO database
        new_user=User(name=name, email=email, password=password_hashata)
        db.session.add(new_user)
        db.session.commit()

        #modifico la costante globale, dopo aver aggiunto il nuovo utente al database
        global oggetto
        oggetto=db.session.execute(db.select(User).where(User.email==email)).scalar()

        return redirect(url_for('get_all_posts'))

    return render_template("register.html")


@app.route('/login', methods=["GET","POST"])
def login():
    if request.method=="POST":

        email=request.form["email"]
        password=request.form["password"]

        #accedo al database e confronto i dati
        global oggetto
        oggetto=db.session.execute(db.select(User).where(User.email==email)).scalar()

        #se lo user non esiste gli invio un messaggio
        if oggetto==None:
            flash('Invalid email provided', 'error')
            return render_template("login.html")

        password_originaria=oggetto.password
        #ottengo dal database il nome dello user:
        name=oggetto.name

        #uso una funzione di werkzeug per confrontare la password inserita con la password hashata salvata.
        #in realtá potrei pure ri-hashare la password inserita e vedere se é uguale a quella salvata
        #ma temo che l'hash non sia identico, perché ogni volta che la password viene hashata viene generato
        #un nuovo salt
        if werkzeug.security.check_password_hash(password_originaria,password):

            #visto che questa volta ho ereditato dal UserMixin non c'é stato bisogno di dichiarare gli attributi
            #(guarda Tag 68 per confronto)
            #oggetto.is_active=True
            #oggetto.is_authenticated=True
            #oggetto.is_anonymous=False

            login_user(oggetto) #ora la funzione login_user passa l'oggetto probabilmente a load_user, il quale crea
            #una route per quello user solo se lo user si é loggato. Il problema é che il mio oggetto ha bisogno
            #di molti piú metodi e attributi implementati. Quindi devo rifare la mia classe User. L'ho rifatta
            #e chiamata Utente_loggato
            flash('Logged in successfully.')
            return redirect(url_for('get_all_posts'))

        else:
            flash('Password incorrect!',"error")
            return render_template("login.html")

    return render_template("login.html")



@app.route("/logout")
def logout():
    logout_user()
    global oggetto
    oggetto=None
    return redirect(url_for('get_all_posts'))

#----------------------------------------------- CREO BLOG ------------------------------------------------------------



@app.route('/<post_id>', methods=["POST","GET"])
def show_post(post_id):

    #innanzitutto voglio l'id dello user, per sapere se l'html del post deve mostrare il bottone edit post o no
    global oggetto
    try:
        id_persona=oggetto.id
    except:
        id_persona=None

    #poi voglio che la pagina web mostri tutti i commenti pubblicati. Commenti in cui l'attributo id é uguale
    #all'id del post

    commenti=db.session.execute(db.select(Comment).where(Comment.blog_post_id_genitore==post_id)).scalars()

    #ottengo l'oggetto che corrisponde all'id del post
    oggetto_post=db.session.execute(db.select(BlogPost).where(BlogPost.id==post_id)).scalar()

    #creo un formulario per i commenti
    form_comment=FormComment()

    #creo un'immaginetta per ogni user
    gravatar = Gravatar(app,
                    size=50,
                    rating='g',
                    default='retro',
                    force_default=False,
                    use_ssl=False,
                    base_url=None)


    if form_comment.validate_on_submit():

        #se qualcuno clicca su comment controllo prima che sia loggato
        try:
            login_user(oggetto)
        except:
            flash("You must login first to comment!", "error")
            return redirect(url_for("login"))

        #a questo punto ottengo l'id della persona loggata
        id_persona=oggetto.id

        #poi ottengo il testo
        comment=form_comment.text.data

        #creo un nuovo commento
        nuovo_commento=Comment(comment=comment, user_id=id_persona, blog_post_id_genitore=oggetto_post.id)
        db.session.add(nuovo_commento)
        db.session.commit()

        #uso redirect in modo che faccia ripartire la funzione da capo (e cancelli il testo che c'é nello
        #spazio del commento
        return redirect(url_for('show_post',post_id=oggetto_post.id))

    return render_template("post.html", post=oggetto_post, id_persona=id_persona, form_comment=form_comment, commenti=commenti,
                           gravatar=gravatar)


@app.route('/make_post', methods=["GET","POST"])
@admin_only
def make_post(**kwargs):

    titolo=request.args.get("titolo")
    print(titolo)

    #il post oggetto é un id!
    #ottengo la variabile con la request di flask
    post_oggetto=request.args.get("post_oggetto")
    #due possibilitá: Uno: il titolo é edit post, allora lútente viene dalla funzione edit_post
    #e allora la funzione make_post deve cambiare una riga di SQLite e non aggiungerne una nuova

    if titolo=="Edit Post":

        print(post_oggetto)
        oggetto_post=db.session.execute(db.select(BlogPost).where(BlogPost.id==int(post_oggetto))).scalar()

        form=Form(title=oggetto_post.title, subtitle=oggetto_post.subtitle, image=oggetto_post.img_url,
                      name=oggetto_post.author, text=oggetto_post.body )

        if form.validate_on_submit():

            title=form.title.data
            subtitle=form.subtitle.data
            author=form.name.data
            print(author)
            image=form.image.data
            text=form.text.data

            oggetto_post.title=title
            oggetto_post.subtitle=subtitle
            oggetto_post.image=image
            oggetto_post.author=author
            oggetto_post.body=text

            db.session.commit()

            return redirect(url_for('get_all_posts'))

    #oppure, seconda possibilitá: il titolo é New Post, allora lútente viene direttamente da index.html
    #e sta cercando di aggiungere un nuovo post nella tabella

    else:

        titolo="New Post"
        form=Form()

        if form.validate_on_submit():

            title=form.title.data
            subtitle=form.subtitle.data
            author=form.name.data
            image=form.image.data
            text=form.text.data

            date=datetime.datetime.now()
            anno=date.year
            giorno=date.month
            mese=date.month
            data= f"{giorno}-{mese}-{anno}"

            #ottengo l'id della persona che si é loggata in questo momento
            global oggetto
            author_id=oggetto.id

            with app.app_context():
                new_post=BlogPost(title=title, subtitle=subtitle, body=text, author=author, img_url=image, date=data,
                                  user_id=author_id)
                db.session.add(new_post)
                db.session.commit()

            return redirect(url_for('get_all_posts'))

    return render_template("make-post.html", form=form, titolo=titolo, post_oggetto=post_oggetto)



@app.route("/edit_post<post_oggetto>", methods=["POST","GET"])
@admin_only
def edit_post(post_oggetto):
    #L html passa i parametri delle funzioni come stringhe!!! Anche se sono oggetti. E neanche gli https riescono a
    #passare oggetti. Quindi adesso passo come variabile un id al posto di tutto l'oggetto intero

    return redirect(url_for('make_post', titolo="Edit Post", post_oggetto=post_oggetto ))

#params={"titolo":"Edit Post", "post_oggetto":post_oggetto}

@app.route("/delete<id>")
def delete(id):
    oggetto=db.session.execute(db.select(BlogPost).where(BlogPost.id==int(id))).scalar()
    db.session.delete(oggetto)
    db.session.commit()
    return redirect(url_for('get_all_posts'))




@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=False, port=5003)

#dalla funzione Python al codice si possono passare oggetti, ma non viceversa
# usa |safe nell'html quando vuoi scrivere un testo che é stato salvato come testo html, ma non vuoi riportare tutti
# i tag dell'html originario (cioé se vuoi solo il testo semplice, senza il codice html)
