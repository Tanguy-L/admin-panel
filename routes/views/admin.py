import json
from flask import jsonify
from flask import Blueprint, render_template, request, redirect
from core.database import get_db
from mysql.connector import Error

views = Blueprint("admin_views", __name__, url_prefix="/admin")

@views.route("/", methods=("GET", "POST"))
def render_admin_home():
    request_method = request.method
    request_form = request.form.to_dict(flat=False)

    if request_method == "POST":

        if ("edit" in request_form.keys()):
            del request_form["edit"]
            return redirect("/admin/?edit=true")

        if ("save" in request_form.keys()):
            del request_form["save"]
            save_members_edit(request_form)
            


    db = get_db()

    members = get_members()
    return render_template("admin/dashboard.html", members=members)

@views.route("/change_team", methods=["POST"])
def change_team():
    data = request.json
    team_id = data.get('team_id')
    member_id = data.get('member_id')

    if team_id is None or member_id is None:
        return jsonify({"error": "Missing team_id or member_id"}), 400

    print(f"{team_id}")

    try:
        connection, cursor = get_db()
        check_query = "SELECT COUNT(*) as count FROM team_members WHERE member_id = %s"
        cursor.execute(check_query, (member_id,))
        count = cursor.fetchall()[0]['count']

        print(f"{count}")

        if count > 0:
            update_query="UPDATE team_members SET team_id = %s WHERE member_id=%s"
            cursor.execute(update_query, (team_id, member_id))
            message = "Existing member's team updated successfully"
        else:
            insert_query = "INSERT INTO team_members (member_id, team_id) VALUES (%s, %s)"
            cursor.execute(insert_query, (member_id, team_id))
            message = "New member added successfully"

        connection.commit()

        return jsonify({"message": message}), 200

    except Exception as e:
        connection.rollback()
        print(f"Error while updating records: {e}")
        return jsonify({"error": str(e)}), 500

@views.route("/teams", methods=("GET", "POST"))
def render_admin_teams():
    request_method = request.method
    request_form = request.form.to_dict(flat=False)

    if request_method == "POST":

        if ("clear-teams" in request_form.keys()):
            del request_form["clear-teams"]
            clear_teams()
            return redirect("/admin")
        
        if ("generate-teams" in request_form.keys()):
            del request_form["generate-teams"]
            generate_teams()
            return redirect("/admin/teams")

    teams = get_teams()
    return render_template("admin/teams.html", teams=teams)

def get_members():
    db, cursor = get_db()  # Assuming you're using the get_db() function we defined earlier
    query = """SELECT m.*, t.team_id, t.name as team_name, t.channel_id as team_channel_id
               FROM members m
               LEFT JOIN team_members tm ON m.id = tm.member_id
               LEFT JOIN teams t ON tm.team_id = t.team_id"""
    cursor.execute(query)
    members = cursor.fetchall()
    return members

def element_exists(list_of_dicts, name_to_find):
    return next((item for item in list_of_dicts if item.get('name') == name_to_find), None)

def get_teams():
    db, cursor = get_db()

    queryTeams = """SELECT t.team_id, t.name, t.channel_id
                FROM teams t"""
    
    cursor.execute(queryTeams)
    teams = cursor.fetchall()
    
    query = """ SELECT t.team_id, t.name, t.channel_id, m.discord_name as player_name, m.id as player_id, m.discord_name as player_name, m.weight as player_weight
                FROM teams t
                LEFT JOIN team_members tm ON t.team_id = tm.team_id
                LEFT JOIN members m ON m.id = tm.member_id
                WHERE m.discord_name IS NOT NULL"""


    cursor.execute(query)
    teamPlayers = cursor.fetchall()

    teams_result = []
    for team in teams:
        teams_result.append({"name": team['name'], "id": team["team_id"], "weight": 0, "players": []})

    for teamPlayer in teamPlayers:
        existing_team = element_exists(teams_result, teamPlayer['name'])
        if existing_team:
            existing_team['weight']+=teamPlayer['player_weight']
            existing_team['players'].append({"id":teamPlayer['player_id'], "name": teamPlayer['player_name'], "weight": teamPlayer['player_weight']})

    print("test")
    
    return teams_result

def check_has_team_member(id):
    connection, cursor  = get_db()

    check_query = "SELECT COUNT(*) as count FROM team_members WHERE member_id = %s"

    cursor.execute(check_query, (id,))
    count = cursor.fetchall()[0]['count']

    print(f"{count}")
    return count > 0

@views.route("/generate_teams", methods=("GET", "POST"))
def generate_teams():
    connection, cursor  = get_db()

    cursor.execute("SELECT * FROM members WHERE weight > 0 AND steam_id IS NOT NULL AND is_logged_in = 0 ORDER BY weight DESC")
    membersNotLogged = cursor.fetchall()

    cursor.execute("SELECT teams.team_id FROM teams WHERE teams.name = 'NoTeam'")
    teamNo = cursor.fetchall()[0]

    for memberNotLogged in membersNotLogged:
        member_not_logged_id = memberNotLogged["id"]

        if check_has_team_member(memberNotLogged["id"]):
            update_query="UPDATE team_members SET team_id='%s' WHERE member_id = %s"
            cursor.execute(update_query, (teamNo["team_id"], member_not_logged_id))
            connection.commit()
        else:
            insert_query = "INSERT INTO team_members (member_id, team_id) VALUES (%s, %s)"
            cursor.execute(insert_query, (member_not_logged_id, teamNo["team_id"]))



    cursor.execute("SELECT * FROM members WHERE weight > 0 AND steam_id IS NOT NULL AND is_logged_in = 1 ORDER BY weight DESC")
    members = cursor.fetchall()

    if not members:
            print("No members found matching the criteria")
            return

    ketchup_weight = 0
    mayo_weight = 0
    
    for member in members:
        new_party = None
        member_id = member["id"]

        if mayo_weight <= ketchup_weight:
            new_party = 1
            mayo_weight += member["weight"]
        else:
            new_party = 3
            ketchup_weight += member["weight"]

        check_query = "SELECT COUNT(*) as count FROM team_members WHERE member_id = %s"

        cursor.execute(check_query, (member['id'],))
        count = cursor.fetchall()[0]['count']

        print(f"{count}")

        if count > 0:
            update_query="UPDATE team_members SET team_id='%s' WHERE member_id = %s"
            cursor.execute(update_query, (new_party, member_id))
            message = "Existing member's team updated successfully"
        else:
            insert_query = "INSERT INTO team_members (member_id, team_id) VALUES (%s, %s)"
            cursor.execute(insert_query, (member_id, new_party))
            message = "New member added successfully"

        connection.commit()

    return jsonify({"message": "Success, load all members in teams Mayo/Ketchup"}), 200

def save_members_edit(request_form):
    connection, cursor = get_db()
    
    try:
        query = "UPDATE members SET steam_id=%s, weight=%s, smoke_color=%s WHERE discord_id=%s"
        
        values = (
            request_form.get('steam_id', [None])[0],
            request_form.get('weight', [None])[0],
            request_form.get('smoke_color', [None])[0],
            request_form.get('discord_id', [None])[0]
        )

        cursor.execute(query, values)
        connection.commit()
        print(f"Updated member data: discord_id={values[3]}, steam_id={values[0]}, weight={values[1]}, smoke_color={values[2]}")
    except Error as e:
        print(f"Error while updating records: {e}")
        connection.rollback()
    finally:
        pass

def clear_teams():
    connection, cursor  = get_db()

    cursor.execute("SELECT * FROM members WHERE weight > 0 AND steam_id IS NOT NULL ORDER BY weight DESC")
    membersNotLogged = cursor.fetchall()

    cursor.execute("SELECT teams.team_id FROM teams WHERE teams.name = 'NoTeam'")
    team = cursor.fetchall()[0]

    if team is None:
        print("noteam is undefined")

    for memberNotLogged in membersNotLogged:
        member_not_logged_id = memberNotLogged["id"]
        update_query="UPDATE team_members SET team_id='%s' WHERE member_id = %s"
        cursor.execute(update_query, (team["team_id"], member_not_logged_id))
        connection.commit()