We removed foreign keys from the ER/UML diagram, since they are not a conceptual-level element. 

We also removed the constraint in the relational schema that user_responses table must reference user_accounts with a foreign key. 
To allow for anonymous use as the comment suggests, we moved the foreign key constraint to the user_accounts table instead.
