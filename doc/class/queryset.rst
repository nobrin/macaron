====================
 QuerySet reference
====================

.. warning:: 

   This reference is under construction.

.. module:: macaron

.. class:: QuerySet


Example
=======

::

    # Creating new team and appending members
    new_team = Team.create(name="Houkago Tea Time")
    new_team.members.append(first_name="Azusa", last_name="Nakano", part="Gt2", age=16)
    new_team.members.append(first_name="Sawako", last_name="Yamanaka", part="Gt1", age=28)
    
    # Retrieving member, updating
    azusa = Member.get("first_name=?", ["Azusa"])
    sawako = Member.get(2)  # Getting with ID
    sawako.part = "Vo"
    sawako.save()       # Reflecting to database
    
    # Deleting
    azusa.delete()
    sawako.delete()

