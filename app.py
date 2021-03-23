from flask import Flask, render_template, redirect, url_for, request, make_response
from flask_wtf import FlaskForm
from wtforms import TextField, PasswordField

import psycopg2
import time
# Подгрузка билбиотек flask'a и postgreSQL'я 

############################################################################       app

app = Flask(__name__) # сам flask 
app.config['SECRET_KEY'] = "helloasdasdsa" # настройка нужна для работы flask_wtf ( формы на странице)

############################################################################ 

gate = True
while gate:
	try:
		conn = psycopg2.connect(dbname='projbase', user='admn', password='adminn', host='postgres') # подключились к базе данных postgres на локальном докере(который появится при сборке, поэтому здесь host='postgres', сама база и пользователь с паролем создаются в init.sql 
		cur = conn.cursor() # через cur выполняем запросы 
		conn.commit() # подстраховка что preinst.py выполнил все команды 
	except:
		print("Not ready preinst")
		time.sleep(1)
	else:
		print("Preinstalling..")
		gate = False

############################################################################       classes

# ниже два класса, которые отвечают за формы на двух страницах(логина и регистраци)

class LoginForm(FlaskForm): # класс которые описывает какие формы появятся на страницу    
    login = TextField('login') # создастя текстовое поле и к нему можно будет обращаться по <class>.login 
    passwd = PasswordField('passwd') # создается поле в котором будет пароль, поэтому все в звездочках при вводе 
    
class RegForm(FlaskForm): 
    login = TextField('login')
    passwd = PasswordField('passwd')
    secpasswd = PasswordField('secpasswd')    

############################################################################       routes


@app.route('/', methods=['GET', 'POST']) # это привязка в flask, указано по какому запросу сюда попадаем, и какие методы можно делать 
def mn():
    log = request.cookies.get('username') # используем cookie 
    if log == 'none' or log == None: # её может не быть(значение None) , либо мы её затерли словом 'none' ( когда делали logut)
        return render_template('index.html'); # если cookie нет, то показываем основноую страницу 
    else:
        return redirect(url_for('chat')) # если есть, то посылаем сразу в чат, url_for просто создает ссылку на функцию chat, а redirect возвращает ответ, в котором сказано перенаправить на такую-то ссылку 


@app.route('/register', methods=['GET', 'POST']) 
def register():
    log = request.cookies.get('username')
    if log == 'none' or log == None: # если cookie нет, то пользователь не залогинен и все хорошо, он может регистрироваться 
        form = RegForm()   # использование класса который выше описали 
        if request.method == 'POST': # если на эту страницу пришли с запросом POST, значит пользоваетль на ней уже был и нажал кнопку регистрации 
            if form.passwd.data == form.secpasswd.data: # проверка повторного пароля 
		# дальше мы используем form.login.data это обращение к странице, просмотр формочки login и забирание из нее информации
                cur.execute("select * from users where login='" + form.login.data + "';") # проверка, есть ли такой пользователь уже в базе 
                rows = cur.fetchall() # это просто достали результат прошлого запроса в виде таблицы со строками 
            
                if len(rows) == 1:  #Если пользователя нашли, значит регистрировать не надо 
		    # здесь в render_template появилось message, это мы сообщили register.html что у него есть поле message в котором есть уже какие-то данные и он может ими пользоваться
                    return render_template('register.html', message='User already exists!') # показываем страницу, но сообщая об ошибке 
                else: # все хорошо, пароль повторный совпал, пользователя нет, значит можем регистрировать 
                    cur.execute("insert into users (login, password) values('" + form.login.data + "', '" + form.passwd.data + "');") # регистрация - вставка данных в базу 
                    conn.commit()  # говорим базе запомнить изменения 
                    return redirect(url_for('login')) # пользователь зарегистрировался, пусть теперь залогинится 
            else:
                return render_template('register.html', message='Passwords are different!') # показываем страницу, но сообщая об ошибке 
        return render_template('register.html') # показываем страницу 
    else: # если cookie есть, то послыаем на главную страницу, а там его перепошлют в чат
        return redirect(url_for('mn'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    log = request.cookies.get('username') 
    if log == 'none' or log == None: # снова проверка, вдруг уже залогинился и как-то попал на эту страницу
        form = LoginForm() # использование класса 
        if request.method == 'POST': # нажал на кнопку "Sign in" 
	    
            cur.execute("select * from users where login='" + form.login.data + "' and password = '" + form.passwd.data + "';") # смотрим пользователя с таким логином и паролем в базе 
            rows = cur.fetchall() 
            
            if len(rows) == 1: # пользователь нашелся 
                res = make_response(redirect(url_for('chat'))) # здесь мы хотим перенаправить на чат, но прежде задать cookie что человек залогинился, для этого мы создали ответ
                res.set_cookie('username', form.login.data) # и в этом ответе дополнительно укажем cookie 
                return res 
            else:
                return render_template('login.html', message='Invalid login or password!', form=form) # возврат ошибки
        else:
            return render_template('login.html', form=form)
    else:
        return redirect(url_for('mn'))


@app.route('/chat', methods=['GET', 'POST']) # либо мы попали просто в чат 
@app.route('/chat/<friend>', methods=['GET', 'POST']) # либо мы уже в чате и выбрали с кем ведем диалог 
def chat(friend=''): # <friend> выше и friend='' одни и теже 
    log = request.cookies.get('username') 
    if log == 'none' or log == None:
        return redirect(url_for('mn')) #если не залогинен, то не может общаться 
    
    cur.execute("select * from friends where main='" + log + "';") # смотрим список друзей 
    rows = cur.fetchall()
    friends = [i[2] for i in rows] # дальше мы его уже будем показывать на странице 
    
    messages=[]
    if friend == '': # друг не выбран, значит сообщения не надо показывать (т.к. не с кем) 
        return render_template('chat.html', log=log, friend=friend, friends=friends, messages=messages, isfr=(len(friends) != 0))   
    
    cur.execute("select * from friends where main = '" + log + "' and frnd = '" + friend + "';") 
    rows = cur.fetchall()
    
    if len(rows) != 1:
        return render_template('chat.html', log=log, friend=friend, friends=friends, messages=messages, isfr=(len(friends) != 0)) # если так вышло, что выбран друг которого нет в друзьях, то просто покажем чат
    
    cur.execute("select * from chat where from_user = '" + log + "' and to_user = '" + friend + "' or from_user = '" + friend + "' and to_user = '" + log + "';") # смотрим сообщения 
    rows = cur.fetchall()
    messages = rows[::-1] # в порядке времени их показываем (самые новые вверху) 
    
    return render_template('chat.html', log=log, friend=friend, friends=friends, messages=messages, isfr=(len(friends) != 0))


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    log = request.cookies.get('username')
    if log == 'none' or log == None:
        return redirect(url_for('mn'))
    if request.method == 'GET': # если попали на эту страницу, а не нажали кнопку "logout" то просто отправим на основную 
        return redirect(url_for('mn'))  
    res = make_response(redirect(url_for('mn'))) # здесь просто затираем имя пользователя словом 'none'  
    res.set_cookie('username', 'none')
    return res


@app.route('/add_message', methods=['GET', 'POST'])
def add_message():
    log = request.cookies.get('username')
    if log == 'none' or log == None:
        return redirect(url_for('mn')) 
    if request.method == 'GET':
        return redirect(url_for('mn')) # аналогично: при нажатии на кнопку метод будет только post
    friendname = request.form['frnd'] # из формы забрали имя, с кем мы ведем диалог(переписку) 
    if friendname == '' or friendname == log or friendname == None or friendname == 'none' or friendname == 'None': # проверка на ошибки 
        return redirect(url_for('chat'))
    
    cur.execute("select * from friends where main = '" + log + "' and frnd = '" + friendname + "';") # смотрим друзей 
    rows = cur.fetchall()
    if len(rows) != 1:
        return redirect(url_for('chat')) # проверка, что такой друг существует
    
    text = request.form['text'] # получили из формы текст сообщения 
    
    cur.execute("insert into chat(from_user, to_user, text, timeofmes) values('" + log + "', '" + friendname + "', '" + text + "', (SELECT 'now'::timestamp));") # довабляем в базу сообщение 
    conn.commit() # запоминем 
    
    return redirect(url_for('select_friend', friendname=friendname)) # отправляем на страницу выбора друга, с уже известным другом, поэтому нас перенаправит в чат с выбранным другом


@app.route('/add_friend', methods=['GET', 'POST'])
def add_friend():
    log = request.cookies.get('username')
    if log == 'none' or log == None:
        return redirect(url_for('mn'))
    if request.method == 'GET':
        return redirect(url_for('mn'))
    
    friendname = request.form['friendname'] # получили имя 
    if friendname == '' or friendname == log: # проверили 
        return redirect(url_for('chat'))
    
    cur.execute("select * from friends where frnd = '" + friendname + "' and main = '" + log + "';") # проверка, нет ли его уже в друзьях 
    rows = cur.fetchall()
    if len(rows) >= 1:
        return redirect(url_for('chat'))
    
    cur.execute("SELECT * from users where login='" + friendname + "';")
    rows = cur.fetchall()
    
    if len(rows) != 1:
        return redirect(url_for('chat')) # проверка что такой пользователь вообще существует 
    
    cur.execute("insert into friends(main, frnd) values('" + log + "', '" + friendname + "');") # добавляем в бд 
    conn.commit()
    
    return redirect(url_for('chat'))


@app.route('/select_friend/<friendname>', methods=['GET', 'POST'])
def select_friend(friendname=''):
    log = request.cookies.get('username')
    if log == 'none' or log == None:
        return redirect(url_for('mn'))
    return redirect(url_for('chat', friend=friendname.split('+')[0])) # friendname заполнится '+' мы их просто удаляем 


@app.route('/del_friend', methods=['GET', 'POST'])
def del_friend():
    log = request.cookies.get('username')
    if log == 'none' or log == None:
        return redirect(url_for('mn'))
    if request.method == 'GET':
        return redirect(url_for('mn'))
    
    friendname = request.form['buttdel']
    if friendname == '' or friendname == log:
        return redirect(url_for('chat'))
    
    cur.execute("select * from friends where frnd = '" + friendname + "' and main = '" + log + "';")
    rows = cur.fetchall()
    
    if len(rows) != 1:
        return redirect(url_for('chat'))
    
    cur.execute("delete from friends where main='" + log + "' and frnd='" + friendname + "';")
    conn.commit()
    
    return redirect(url_for('chat'))

############################################################################       end

if __name__ == '__main__':
    app.run(debug = False, host='0.0.0.0') # запуск приложения на flask'e 
