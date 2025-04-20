#! /usr/bin/python3
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_mysqldb import MySQL
import json
import MySQLdb.cursors
import MySQLdb.cursors, re, hashlib

app = Flask(__name__)
app.secret_key='your secret key'

#Configuration for flask_mysqldb
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root' 
app.config['MYSQL_PASSWORD'] = '' 
app.config['MYSQL_DB'] = '' 

mysql = MySQL(app) 

@app.route('/',methods=['GET','POST'])
def login():
    #output a message if something goes wrong
    msg=''
    #check if "username" and "password" POST requests exist(user submitted form)
    if request.method=='POST' and 'username' in  request.form and 'password' in request.form:
    #create variables for easy access
        username=request.form['username']
        password=request.form['password']

        hash=password+app.secret_key
        hash=hashlib.sha1(hash.encode())
        password=hash.hexdigest()

        #check is account exists using MySQL
        cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username =%s AND password=%s', (username, password,))
        #Fetch one record and return the result
        account=cursor.fetchone()
        #if account exists in accounts table in our database
        if account:
            #create session data to access in other routes
            session['loggedin']=True
            session['id']=account['id']
            session['username']=account['username']
            #Redirect to home page
            return redirect(url_for('home'))
        else:
            #Account doesn't exist or username/password incorrect
            msg='Incorrect username and/or password!'
    #show the login form with message (if any)
    return render_template('index.html',msg=msg)
  
@app.route('/logout')
def logout():
        #remove session data to logout user
        session.pop('loggedin', None)
        session.pop('id', None)
        session.pop('username', None)
        #redirect to login
        return redirect(url_for('login'))

@app.route('/register',methods=['GET','POST'])
def register():
        #output message if stuff goes sideways
        msg=''
        #check if 'username','password', and 'email' POST requests exists (user submitted form)
        if request.method=='POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
            username=request.form['username']
            password=request.form['password']
            email=request.form['email']
            # Check if account exists using MySQL
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
            account = cursor.fetchone()
            # If account exists show error and validation checks
            if account:
                msg = 'Account already exists!'
            elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                msg = 'Invalid email address!'
            elif not re.match(r'[A-Za-z0-9]+', username):
                msg = 'Username must contain only characters and numbers!'
            elif not username or not password or not email:
                msg = 'You have to fill out the form, goofball.'
            else:
                # Hash the password
                hash = password + app.secret_key
                hash = hashlib.sha1(hash.encode())
                password = hash.hexdigest()
                # Account doesn't exist, and the form data is valid, so insert the new account into the accounts table
                cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, password, email,))
                mysql.connection.commit()
                msg = 'You have successfully registered!'
        elif request.method=='POST':
             #empty form, no POST data
            msg='Fill out the form, butthead.'
        #show registeration form with message (if any)
        return render_template('register.html', msg=msg)

@app.route('/home')
def home():
     #check to see if the user is logged in
    if 'loggedin' in session:
        #user is logged in, so show them the home page
        return render_template ('home.html', username=session['username'])
    #user not logged in, redirect to login
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
     #check to see if user is logged in
     if 'loggedin' in session:
        #we need user account info to display
        cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE id= %s', (session['id'],))
        account=cursor.fetchone()
        #show profile page with account info
        return render_template('profile.html', account=account)
     #user not logged in; redirect to login page
     return redirect(url_for('login'))

@app.route('/searchform')
def searchform():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    return render_template('form.html', username=session['username'])

# Search route
@app.route('/search', methods=['POST', 'GET'])
def search():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if request.method == 'GET':
        return "Fill out the Search Form"
     
    if request.method == 'POST':
        name = request.form['name']
        id = request.form['id']
        cursor = mysql.connection.cursor()
        
        query="SELECT * FROM student"
        filters=[]
        if name:
            filters.append(f"name LIKE '%{name}%'")
           # cursor.execute("SELECT * from student WHERE name LIKE %s", [f"%{name}%"])  
        if id:
            filters.append(f"ID LIKE '%{id}%'")
            #cursor.execute("SELECT * from student where ID LIKE %s", [f"%{id}%"])
        if filters:
            query+=" WHERE " + " AND ".join(filters)
       
        cursor.execute(query)
        #mysql.connection.commit()
        data = cursor.fetchall()
        cursor.close()
        return render_template('results.html', data=data)

@app.route('/newstudent', methods=['POST', 'GET'])
def newstudent():
    if'loggedin' not in session:
        return redirect(url_for('login'))
    if request.method == 'GET':
        cursor=mysql.connection.cursor()
        cursor.execute('SELECT * FROM student')
        departments=[row[2] for row in cursor.fetchall()]
        cursor.close()
        return render_template('newstudent.html', departments=departments)
        
    if request.method == 'POST':
        name = request.form['name']
        id = request.form['id']
        dept_name = request.form['dept_name']        
        tot_cred = request.form['tot_cred']
        cursor = mysql.connection.cursor()
        cursor.execute("Insert into student values(%s, %s, %s, %s)",[id, name, dept_name, tot_cred])
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('home'))
        
@app.route('/schedule/<student_id>', methods=['GET'])
def schedule(student_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    year_filter=request.args.get('year')
    
    cursor = mysql.connection.cursor()
    query ="""
        SELECT s.ID, s.name, t.course_id, t.semester, t.year
        FROM student s
        JOIN takes t ON s.ID = t.ID
        WHERE s.ID = %s
    """
    params=[student_id]
    if year_filter:
        query += " AND t.year = %s"
        params.append(year_filter)

    cursor.execute(query, params)
    schedule_data = cursor.fetchall()
    
    # Get distinct years for the dropdown filter
    cursor.execute("SELECT DISTINCT year FROM takes WHERE ID = %s", [student_id])
    years = [row[0] for row in cursor.fetchall()]
    cursor.close()
    
    return render_template('schedule.html', schedule_data=schedule_data, years=years, student_id=student_id)
    
   

if __name__=="__main__":
    app.run()
