# data_manager.py
import sqlite3
from datetime import datetime

DATABASE_NAME = 'hotel_pos.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row 
    return conn

# --- GESTION DES CHAMBRES (CRUD) ---
def get_all_rooms():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, numero, type_chambre, prix_nuit, statut FROM chambres ORDER BY numero")
    rooms = cursor.fetchall()
    conn.close()
    return rooms

def get_room(room_id):
    """(ADMIN) Récupère les détails d'une chambre par ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, numero, type_chambre, prix_nuit FROM chambres WHERE id = ?", (room_id,))
    room = cursor.fetchone()
    conn.close()
    return room

def add_room_type(numero, type_chambre, prix_nuit):
    """(ADMIN) Ajoute une nouvelle chambre."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO chambres (numero, type_chambre, prix_nuit) VALUES (?, ?, ?)", 
                       (numero, type_chambre, prix_nuit))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False 
    finally:
        conn.close()

def delete_room(room_id):
    """(ADMIN) Supprime une chambre par ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # On vérifie si la chambre est occupée
        cursor.execute("SELECT COUNT(*) FROM sejours WHERE chambre_id = ? AND date_checkout_reelle IS NULL", (room_id,))
        if cursor.fetchone()[0] > 0:
            return False # Ne peut pas supprimer une chambre occupée
            
        cursor.execute("DELETE FROM chambres WHERE id = ?", (room_id,))
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def update_room(room_id, numero, type_chambre, prix_nuit):
    """(ADMIN) Met à jour les détails d'une chambre."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE chambres
            SET numero = ?, type_chambre = ?, prix_nuit = ?
            WHERE id = ?
        """, (numero, type_chambre, prix_nuit, room_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erreur lors de la mise à jour de la chambre : {e}")
        return False
    finally:
        conn.close()

# --- GESTION DES PRODUITS (CRUD) ---
def get_all_products(user_role=None):
    """
    Récupère les produits/services.
    Filtre pour les 'Services Auxiliaires' si le rôle est 'Réceptionniste'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM produits_services WHERE type_vente != 'Hébergement'"
    params = []

    if user_role == 'Réceptionniste':
        query += " AND type_vente = ?"
        params.append('Service Auxiliaire')

    query += " ORDER BY categorie, nom"

    cursor.execute(query, params)
    products = cursor.fetchall()
    conn.close()
    return products

def get_product(product_id):
    """(ADMIN) Récupère les détails d'un produit par ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nom, prix_unitaire, type_vente, categorie FROM produits_services WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()
    return product

def add_product(nom, prix_unitaire, type_vente, categorie):
    """(ADMIN) Ajoute un nouveau produit/service."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO produits_services (nom, prix_unitaire, type_vente, categorie) 
            VALUES (?, ?, ?, ?)
        """, (nom, prix_unitaire, type_vente, categorie))
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def delete_product(product_id):
    """(ADMIN) Supprime un produit par ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Idéalement, on vérifierait si le produit est dans d'anciennes commandes
        # Mais pour l'instant, suppression simple
        cursor.execute("DELETE FROM produits_services WHERE id = ?", (product_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Le produit est lié à une ligne_commande
        return False 
    finally:
        conn.close()

def update_product(product_id, nom, prix_unitaire, type_vente, categorie):
    """(ADMIN) Met à jour les détails d'un produit."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE produits_services
            SET nom = ?, prix_unitaire = ?, type_vente = ?, categorie = ?
            WHERE id = ?
        """, (nom, prix_unitaire, type_vente, categorie, product_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erreur lors de la mise à jour du produit : {e}")
        return False
    finally:
        conn.close()

# --- GESTION DES SÉJOURS (CHECK-IN / CHECK-OUT) ---
# (Toutes les fonctions de l'étape précédente restent ici - inchangées)
def get_active_stays():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT s.id, c.numero, s.client_nom, s.date_checkin, s.solde_actuel FROM sejours s JOIN chambres c ON s.chambre_id = c.id WHERE s.date_checkout_reelle IS NULL ORDER BY c.numero"
    cursor.execute(query)
    stays = cursor.fetchall()
    conn.close()
    return stays

def get_available_rooms_for_period(start_date, end_date):
    """
    Retourne les chambres qui ne sont ni occupées (séjour en cours)
    ni réservées pendant la période spécifiée.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT * FROM chambres
        WHERE id NOT IN (
            -- Exclure les chambres avec des séjours qui se chevauchent
            SELECT chambre_id FROM sejours
            WHERE date_checkout_reelle IS NULL -- Séjours actifs

            UNION

            -- Exclure les chambres avec des réservations qui se chevauchent
            SELECT chambre_id FROM reservations
            WHERE statut = 'Confirmée'
              AND date_debut < ?
              AND date_fin > ?
        )
        ORDER BY numero
    """

    cursor.execute(query, (end_date, start_date))
    rooms = cursor.fetchall()
    conn.close()
    return rooms

def create_new_stay(room_id, client_name, date_checkout_prevue):
    conn = get_db_connection()
    cursor = conn.cursor()
    date_checkin = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("INSERT INTO sejours (chambre_id, client_nom, date_checkin, date_checkout_prevue, statut) VALUES (?, ?, ?, ?, 'Ouvert')", 
                       (room_id, client_name, date_checkin, date_checkout_prevue))
        update_room_status(room_id, 'Occupée')
        conn.commit()
        return True
    except sqlite3.Error as e: return False
    finally: conn.close()

# --- GESTION DES RÉSERVATIONS ---
def create_reservation(chambre_id, client_nom, date_debut, date_fin):
    """Crée une nouvelle réservation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO reservations (chambre_id, client_nom, date_debut, date_fin)
            VALUES (?, ?, ?, ?)
        """, (chambre_id, client_nom, date_debut, date_fin))
        # Mettre à jour le statut de la chambre
        update_room_status(chambre_id, 'Réservée')
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erreur lors de la création de la réservation : {e}")
        return False
    finally:
        conn.close()

def cancel_reservation(reservation_id):
    """Annule une réservation et libère la chambre."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Récupérer l'ID de la chambre pour la mettre à jour
        cursor.execute("SELECT chambre_id FROM reservations WHERE id = ?", (reservation_id,))
        result = cursor.fetchone()
        if not result:
            return False
        room_id = result['chambre_id']

        # Mettre à jour la réservation
        cursor.execute("UPDATE reservations SET statut = 'Annulée' WHERE id = ?", (reservation_id,))

        # Libérer la chambre
        update_room_status(room_id, 'Libre')

        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erreur lors de l'annulation de la réservation : {e}")
        return False
    finally:
        conn.close()

def get_all_reservations():
    """Récupère toutes les réservations à venir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT r.id, c.numero, r.client_nom, r.date_debut, r.date_fin, r.statut
        FROM reservations r
        JOIN chambres c ON r.chambre_id = c.id
        WHERE r.statut = 'Confirmée' AND r.date_fin >= date('now')
        ORDER BY r.date_debut
    """
    cursor.execute(query)
    reservations = cursor.fetchall()
    conn.close()
    return reservations

def update_room_status(room_id, new_status):
    """Met à jour le statut d'une chambre."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE chambres SET statut = ? WHERE id = ?", (new_status, room_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Erreur lors de la mise à jour du statut de la chambre : {e}")
    finally:
        conn.close()

def get_stay_details(stay_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT s.id, c.numero, c.type_chambre, c.prix_nuit, s.client_nom, s.date_checkin, s.date_checkout_prevue, s.solde_actuel FROM sejours s JOIN chambres c ON s.chambre_id = c.id WHERE s.id = ? AND s.date_checkout_reelle IS NULL"
    cursor.execute(query, (stay_id,))
    details = cursor.fetchone()
    conn.close()
    return details

def get_stay_ordered_items(stay_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT p.nom, lc.quantite, lc.prix_unitaire_vente, (lc.quantite * lc.prix_unitaire_vente) AS sous_total FROM lignes_commande lc JOIN produits_services p ON lc.produit_id = p.id JOIN commandes_ventes cv ON lc.commande_id = cv.id WHERE cv.stay_id = ? AND cv.statut_paiement = 'Transféré' ORDER BY cv.date_heure"
    cursor.execute(query, (stay_id,))
    items = cursor.fetchall()
    conn.close()
    return items

def perform_checkout(stay_id, final_bill_amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    date_checkout_reelle = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        # Récupérer l'ID de la chambre avant de clôturer le séjour
        cursor.execute("SELECT chambre_id FROM sejours WHERE id = ?", (stay_id,))
        result = cursor.fetchone()
        if not result:
            return False
        room_id = result['chambre_id']

        cursor.execute("UPDATE sejours SET date_checkout_reelle = ?, solde_actuel = ?, statut = 'Clos' WHERE id = ?", 
                       (date_checkout_reelle, final_bill_amount, stay_id))
        cursor.execute("UPDATE commandes_ventes SET statut_paiement = 'Payé' WHERE stay_id = ?", (stay_id,))

        # Mettre à jour le statut de la chambre
        update_room_status(room_id, 'Libre') # Ou 'Nettoyage' si on veut complexifier

        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erreur lors du checkout : {e}")
        return False
    finally:
        conn.close()

# --- GESTION DU POS ET DES COMMANDES ---
# (Inchangé)
def create_pos_order(user_id, cart_items, payment_type, stay_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    total_net = sum(item['prix'] * item['qte'] for item in cart_items)
    if payment_type == 'Transfert Compte' and stay_id:
        statut_paiement = 'Transféré'
    elif payment_type in ['Espèces', 'Carte', 'Mobile']:
        statut_paiement = 'Payé'
        stay_id = None 
    else: return False
    try:
        cursor.execute("INSERT INTO commandes_ventes (utilisateur_id, stay_id, total_net, statut_paiement, date_heure) VALUES (?, ?, ?, ?, ?)", 
                       (user_id, stay_id, total_net, statut_paiement, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        commande_id = cursor.lastrowid
        lignes_a_inserer = []
        for item in cart_items:
            lignes_a_inserer.append((commande_id, item['id'], item['qte'], item['prix']))
        cursor.executemany("INSERT INTO lignes_commande (commande_id, produit_id, quantite, prix_unitaire_vente) VALUES (?, ?, ?, ?)", lignes_a_inserer)
        cursor.execute("INSERT INTO paiements (commande_id, montant, mode_paiement, date_heure) VALUES (?, ?, ?, ?)", 
                       (commande_id, total_net, payment_type, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        if statut_paiement == 'Transféré':
            cursor.execute("UPDATE sejours SET solde_actuel = solde_actuel + ? WHERE id = ?", (total_net, stay_id))
        conn.commit()
        return commande_id
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Erreur lors de la création de la commande POS : {e}")
        return False
    finally: conn.close()

def get_order_details(order_id):
    """Récupère les détails complets d'une commande pour l'impression du ticket."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Dictionnaire pour stocker les résultats
    details = {}

    # 1. Infos générales sur la commande
    query_order = """
        SELECT
            cv.id,
            cv.date_heure,
            cv.total_net,
            cv.statut_paiement,
            p.mode_paiement,
            u.nom_utilisateur,
            s.client_nom,
            c.numero AS chambre_numero
        FROM commandes_ventes cv
        JOIN utilisateurs u ON cv.utilisateur_id = u.id
        LEFT JOIN paiements p ON cv.id = p.commande_id
        LEFT JOIN sejours s ON cv.stay_id = s.id
        LEFT JOIN chambres c ON s.chambre_id = c.id
        WHERE cv.id = ?
    """
    cursor.execute(query_order, (order_id,))
    order_info = cursor.fetchone()
    if not order_info:
        conn.close()
        return None
    details['order'] = dict(order_info)

    # 2. Lignes de la commande (articles)
    query_items = """
        SELECT
            p.nom,
            lc.quantite,
            lc.prix_unitaire_vente,
            (lc.quantite * lc.prix_unitaire_vente) AS sous_total
        FROM lignes_commande lc
        JOIN produits_services p ON lc.produit_id = p.id
        WHERE lc.commande_id = ?
    """
    cursor.execute(query_items, (order_id,))
    items_info = cursor.fetchall()
    details['items'] = [dict(row) for row in items_info]

    conn.close()
    return details

# --- MODULE REPORTING ---

def get_sales_report(start_date, end_date):
    """
    Génère un rapport de ventes agrégé sur une période donnée.
    """
    # Ajoute l'heure pour couvrir toute la journée de fin
    start_date_sql = f"{start_date} 00:00:00"
    end_date_sql = f"{end_date} 23:59:59"

    conn = get_db_connection()
    cursor = conn.cursor()

    report = {
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': 0,
        'stay_revenue': 0,
        'pos_revenue': 0,
        'payments_breakdown': [],
        'top_products_by_qty': [],
        'top_products_by_value': []
    }

    try:
        # 1. Chiffre d'affaires des séjours clôturés dans la période
        cursor.execute("""
            SELECT SUM(solde_actuel)
            FROM sejours
            WHERE statut = 'Clos' AND date_checkout_reelle BETWEEN ? AND ?
        """, (start_date_sql, end_date_sql))
        stay_revenue = cursor.fetchone()[0] or 0
        report['stay_revenue'] = stay_revenue

        # 2. Chiffre d'affaires des ventes directes du POS (non transférées)
        cursor.execute("""
            SELECT SUM(total_net)
            FROM commandes_ventes
            WHERE statut_paiement = 'Payé' AND date_heure BETWEEN ? AND ?
        """, (start_date_sql, end_date_sql))
        pos_revenue = cursor.fetchone()[0] or 0
        report['pos_revenue'] = pos_revenue

        # 3. Chiffre d'affaires total
        report['total_revenue'] = stay_revenue + pos_revenue

        # 4. Ventilation par mode de paiement (pour les ventes directes)
        cursor.execute("""
            SELECT mode_paiement, SUM(montant) as total
            FROM paiements
            WHERE date_heure BETWEEN ? AND ?
            GROUP BY mode_paiement
            ORDER BY total DESC
        """, (start_date_sql, end_date_sql))
        report['payments_breakdown'] = [dict(row) for row in cursor.fetchall()]

        # 5. Top 5 des produits par quantité vendue
        cursor.execute("""
            SELECT p.nom, SUM(lc.quantite) as total_qty
            FROM lignes_commande lc
            JOIN produits_services p ON lc.produit_id = p.id
            JOIN commandes_ventes cv ON lc.commande_id = cv.id
            WHERE cv.date_heure BETWEEN ? AND ?
            GROUP BY p.nom
            ORDER BY total_qty DESC
            LIMIT 5
        """, (start_date_sql, end_date_sql))
        report['top_products_by_qty'] = [dict(row) for row in cursor.fetchall()]

        # 6. Top 5 des produits par chiffre d'affaires
        cursor.execute("""
            SELECT p.nom, SUM(lc.quantite * lc.prix_unitaire_vente) as total_value
            FROM lignes_commande lc
            JOIN produits_services p ON lc.produit_id = p.id
            JOIN commandes_ventes cv ON lc.commande_id = cv.id
            WHERE cv.date_heure BETWEEN ? AND ?
            GROUP BY p.nom
            ORDER BY total_value DESC
            LIMIT 5
        """, (start_date_sql, end_date_sql))
        report['top_products_by_value'] = [dict(row) for row in cursor.fetchall()]

    except sqlite3.Error as e:
        print(f"Erreur lors de la génération du rapport : {e}")
    finally:
        conn.close()

    return report
