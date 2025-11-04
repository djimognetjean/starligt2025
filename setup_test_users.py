import user_manager

# Crée un utilisateur Réceptionniste s'il n'existe pas
if not user_manager.authenticate_user('reception', 'reception123'):
    user_manager.add_user('reception', 'reception123', 'Réceptionniste')
    print("Utilisateur 'reception' créé.")

# Crée un utilisateur Caissier s'il n'existe pas
if not user_manager.authenticate_user('caisse', 'caisse123'):
    user_manager.add_user('caisse', 'caisse123', 'Caissier')
    print("Utilisateur 'caisse' créé.")
