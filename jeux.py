import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

class Jeux(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # self.data a été supprimé car on utilise maintenant la base de données SQL du main.py
        # La ligne add_command a été supprimée car le main.py s'occupe déjà de la synchronisation

    # =========================
    # 💰 SYSTÈME ARGENT (LIÉ À LA DB SQLITE)
    # =========================

    def get_user(self, user_id):
        # On utilise la connexion 'db' créée dans le MyBot du main.py
        cursor = self.bot.db.cursor()
        cursor.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        
        if res:
            return res[0]
        
        # Si l'utilisateur n'est pas dans la DB, on le crée avec 100€ (valeur par défaut du main.py)
        cursor.execute("INSERT INTO users (user_id, money) VALUES (?, 100)", (user_id,))
        self.bot.db.commit()
        return 100

    def update_money(self, user_id, amount):
        # On met à jour directement la colonne 'money' de la table 'users'
        cursor = self.bot.db.cursor()
        cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, user_id))
        self.bot.db.commit()

    def fmt(self, x):
        return f"{x:,}".replace(",", " ")

    def check_mise(self, mise, minv, maxv, solde):
        if mise < minv:
            return f"❌ Mise minimum : {minv} €"
        if mise > maxv:
            return f"❌ Mise maximum : {maxv} €"
        if solde < mise:
            return "❌ Tu n'as pas assez d'argent"
        return None

    # =========================
    # 🎮 GROUPE
    # =========================

    jeux = app_commands.Group(name="jeux", description="🎮 Jeux du casino")

# ==============================================================================
# 🪙 PILE OU FACE PREMIUM (SYSTÈME AVANCÉ AVEC ANIMATIONS ET STATISTIQUES)
# ==============================================================================

    @jeux.command(name="pileouface", description="🪙 Tente de doubler ta mise sur un lancer de pièce !")
    async def pileouface(self, interaction: discord.Interaction, mise: int):
        """
        Jeu de Pile ou Face avec animations, multiplicateurs de gains
        et connexion à la base de données SQLite.
        """
        user_id = interaction.user.id
        solde_actuel = self.get_user(user_id)

        # 1. Vérification de la mise (Min: 10€, Max: 25 000€)
        erreur = self.check_mise(mise, 10, 25000, solde_actuel)
        if erreur:
            return await interaction.response.send_message(erreur, ephemeral=True)

        # 2. Création de l'Embed de départ
        embed_attente = discord.Embed(
            title="🪙 PILE OU FACE - SALON DES JEUX",
            description=(
                f"**Joueur :** {interaction.user.mention}\n"
                f"**Mise engagée :** `{self.fmt(mise)} €`\n\n"
                "✨ *Faites votre choix ci-dessous pour lancer la pièce !*"
            ),
            color=0x3498DB # Bleu brillant
        )
        embed_attente.set_thumbnail(url="https://i.imgur.com/39p6AAn.png") # Image d'une pièce
        embed_attente.add_field(name="💰 Solde après mise", value=f"{self.fmt(solde_actuel - mise)} €")
        embed_attente.set_footer(text="Le casino vous souhaite bonne chance !")

        # 3. Définition de la View Interne (Boutons)
        class PileOuFaceView(discord.ui.View):
            def __init__(self, cog, user, mise_jouee):
                super().__init__(timeout=45) # 45 secondes pour répondre
                self.cog = cog
                self.user = user
                self.mise = mise_jouee
                self.termine = False

            async def on_timeout(self):
                """Désactive les boutons si le joueur met trop de temps."""
                for item in self.children:
                    item.disabled = True
                try:
                    await self.message.edit(view=self)
                except:
                    pass

            async def lancer_piece(self, i: discord.Interaction, choix_joueur: str):
                if i.user.id != self.user.id:
                    return await i.response.send_message("❌ Ce n'est pas votre mise !", ephemeral=True)

                if self.termine:
                    return

                self.termine = True
                
                # Débit de l'argent immédiatement au clic
                self.cog.update_money(self.user.id, -self.mise)

                # --- ANIMATION DE LANCER ---
                emojis_animation = ["🪙", "🔄", "✨", "🪙", "🔄"]
                for emoji in emojis_animation:
                    embed_anim = discord.Embed(
                        title="🪙 LA PIÈCE TOURNE...",
                        description=f"### {emoji}\n*Le destin est en marche...*",
                        color=0xF1C40F
                    )
                    if not i.response.is_done():
                        await i.response.edit_message(embed=embed_anim, view=None)
                    else:
                        await i.edit_original_response(embed=embed_anim, view=None)
                    await asyncio.sleep(0.5)

                # --- RÉSULTAT ---
                resultat = random.choice(["pile", "face"])
                victoire = (choix_joueur == resultat)
                
                embed_resultat = discord.Embed(timestamp=datetime.now())
                
                if victoire:
                    gain_total = self.mise * 2
                    # On rajoute l'argent gagné (mise * 2)
                    self.cog.update_money(self.user.id, gain_total)
                    
                    embed_resultat.title = "🎊 VICTOIRE ! 🎊"
                    embed_resultat.color = 0x2ECC71 # Vert
                    embed_resultat.description = (
                        f"La pièce est tombée sur : **{resultat.upper()}** !\n\n"
                        f"🔹 **Mise :** `{self.cog.fmt(self.mise)} €`\n"
                        f"🔸 **Gain :** `+{self.cog.fmt(gain_total)} €`"
                    )
                    embed_resultat.set_thumbnail(url="https://i.imgur.com/E8314M1.png") # Image trophée
                else:
                    embed_resultat.title = "💀 PERDU... 💀"
                    embed_resultat.color = 0xE74C3C # Rouge
                    embed_resultat.description = (
                        f"La pièce est tombée sur : **{resultat.upper()}**...\n\n"
                        f"Tu as choisi **{choix_joueur.upper()}**, c'est dommage.\n"
                        f"❌ **Perte :** `-{self.cog.fmt(self.mise)} €`"
                    )
                    embed_resultat.set_thumbnail(url="https://i.imgur.com/6X9m9D7.png") # Image tête de mort

                # Infos de fin
                nouveau_solde = self.cog.get_user(self.user.id)
                embed_resultat.add_field(name="💳 Nouveau Solde", value=f"**{self.cog.fmt(nouveau_solde)} €**")
                embed_resultat.set_footer(text=f"Partie terminée pour {self.user.display_name}")

                await i.edit_original_response(embed=embed_resultat, view=None)

            # Boutons de l'interface
            @discord.ui.button(label="MISER SUR PILE", style=discord.ButtonStyle.primary, emoji="🔵")
            async def btn_pile(self, i: discord.Interaction, button: discord.ui.Button):
                await self.lancer_piece(i, "pile")

            @discord.ui.button(label="MISER SUR FACE", style=discord.ButtonStyle.secondary, emoji="🔴")
            async def btn_face(self, i: discord.Interaction, button: discord.ui.Button):
                await self.lancer_piece(i, "face")

            @discord.ui.button(label="ANNULER", style=discord.ButtonStyle.danger)
            async def btn_cancel(self, i: discord.Interaction, button: discord.ui.Button):
                if i.user.id != self.user.id:
                    return await i.response.send_message("❌ Pas votre jeu !", ephemeral=True)
                
                self.termine = True
                self.stop()
                await i.response.edit_message(content="❌ Partie annulée. Aucun frais débité.", embed=None, view=None)

        # 4. Envoi du message initial
        view = PileOuFaceView(self, interaction.user, mise)
        await interaction.response.send_message(embed=embed_attente, view=view)
        view.message = await interaction.original_response()

# ==============================================================================
# 💡 NOTES POUR L'UTILISATEUR
# ==============================================================================
# 1. Ce code utilise 'self.bot.db' défini dans ton main.py pour SQLite.
# 2. J'ai ajouté une animation de 2.5 secondes pour créer du suspense au casino.
# 3. L'argent est retiré seulement SI le joueur clique sur Pile ou Face.
# 4. Si le joueur clique sur 'Annuler', rien n'est retiré de sa banque.

# ==============================================================================
# 🔢 LE JUSTE NOMBRE - ÉDITION LUXE (ANTI-TRICHE & SÉCURISÉ)
# ==============================================================================

    @jeux.command(name="mystere", description="🔢 Devine si ton nombre caché est plus grand ou plus petit que celui de la banque !")
    async def mystere(self, interaction: discord.Interaction, mise: int):
        """
        Jeu Mystère (Plus haut / Plus bas)
        Sécurité : Débit immédiat, détection d'abandon, et protection contre la triche.
        """
        user_id = interaction.user.id
        solde_actuel = self.get_user(user_id)

        # --- 1. VÉRIFICATIONS DE SÉCURITÉ ---
        limite_min = 10
        limite_max = 50000
        erreur = self.check_mise(mise, limite_min, limite_max, solde_actuel)
        
        if erreur:
            return await interaction.response.send_message(erreur, ephemeral=True)

        # --- 2. GÉNÉRATION DES NOMBRES (CACHÉS) ---
        # On génère tout de suite pour éviter toute manipulation après le clic
        nombre_banque = random.randint(1, 100)
        nombre_joueur = random.randint(1, 100)

        # On s'assure qu'il n'y a pas d'égalité parfaite dès le départ pour le fun
        while nombre_joueur == nombre_banque:
            nombre_joueur = random.randint(1, 100)

        # --- 3. DÉBIT IMMÉDIAT ---
        # Le casino encaisse la mise avant même que le joueur ne choisisse
        self.update_money(user_id, -mise)

        # --- 4. INTERFACE VISUELLE ---
        embed = discord.Embed(
            title="🔢 JEU MYSTÈRE - LA BANQUE A JOUÉ",
            description=(
                f"La banque a tiré son nombre : **` {nombre_banque} `**\n\n"
                "Le tien est actuellement caché sous cette carte : 🎴\n"
                "**Penses-tu que ton nombre est plus HAUT ou plus BAS ?**"
            ),
            color=0x9B59B6 # Violet Royal
        )
        embed.add_field(name="💰 Mise engagée", value=f"`{self.fmt(mise)} €`", inline=True)
        embed.add_field(name="🎰 Gain possible", value=f"`{self.fmt(mise * 2)} €`", inline=True)
        embed.set_footer(text="Si tu quittes maintenant, ta mise est définitivement perdue !")
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)

        # --- 5. LOGIQUE DE LA VIEW (ANTI-ABANDON) ---
        class MystereView(discord.ui.View):
            def __init__(self, cog, user, mise_jouee, n_banque, n_joueur):
                super().__init__(timeout=30) # 30 secondes pour décider
                self.cog = cog
                self.user = user
                self.mise = mise_jouee
                self.n_banque = n_banque
                self.n_joueur = n_joueur
                self.action_faite = False

            async def on_timeout(self):
                """En cas d'abandon (timeout), l'argent n'est pas rendu."""
                if not self.action_faite:
                    for item in self.children:
                        item.disabled = True
                    
                    abandon_embed = discord.Embed(
                        title="⏱️ TEMPS ÉCOULÉ : ABANDON",
                        description=(
                            f"Tu as mis trop de temps à choisir...\n"
                            f"Le casino garde ta mise de **{self.cog.fmt(self.mise)} €**.\n\n"
                            f"Ton nombre était : **{self.n_joueur}**"
                        ),
                        color=0x2C2F33 # Gris sombre
                    )
                    try:
                        await self.message.edit(embed=abandon_embed, view=None)
                    except:
                        pass

            async def process_choice(self, i: discord.Interaction, choix: str):
                # Protection contre les curieux
                if i.user.id != self.user.id:
                    return await i.response.send_message("❌ Ce jeu appartient à quelqu'un d'autre !", ephemeral=True)

                if self.action_faite:
                    return

                self.action_faite = True
                self.stop() # Arrête le timer

                # Détermination du gagnant
                gagne = False
                if choix == "haut" and self.n_joueur > self.n_banque:
                    gagne = True
                elif choix == "bas" and self.n_joueur < self.n_banque:
                    gagne = True

                # Création du résultat final
                res_embed = discord.Embed(timestamp=datetime.now())
                
                if gagne:
                    gain = self.mise * 2
                    self.cog.update_money(self.user.id, gain)
                    
                    res_embed.title = "✅ VICTOIRE ÉCLATANTE !"
                    res_embed.color = 0x2ECC71 # Vert
                    res_embed.description = (
                        f"La banque avait : **{self.n_banque}**\n"
                        f"Ton nombre était : **{self.n_joueur}**\n\n"
                        f"🔥 Excellent choix ! Tu remportes **{self.cog.fmt(gain)} €**"
                    )
                else:
                    res_embed.title = "💀 ÉCHEC DU MYSTÈRE..."
                    res_embed.color = 0xE74C3C # Rouge
                    res_embed.description = (
                        f"La banque avait : **{self.n_banque}**\n"
                        f"Ton nombre était : **{self.n_joueur}**\n\n"
                        f"❌ Perdu ! Ta mise de **{self.cog.fmt(self.mise)} €** est encaissée par la banque."
                    )

                nouveau_solde = self.cog.get_user(self.user.id)
                res_embed.add_field(name="💳 Nouveau Solde", value=f"**{self.cog.fmt(nouveau_solde)} €**")
                res_embed.set_footer(text="Merci d'avoir joué au Casino !")

                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="PLUS HAUT ⬆️", style=discord.ButtonStyle.success)
            async def haut_btn(self, i: discord.Interaction, b: discord.ui.Button):
                await self.process_choice(i, "haut")

            @discord.ui.button(label="PLUS BAS ⬇️", style=discord.ButtonStyle.danger)
            async def bas_btn(self, i: discord.Interaction, b: discord.ui.Button):
                await self.process_choice(i, "bas")

        # --- 6. ENVOI DU JEU ---
        view = MystereView(self, interaction.user, mise, nombre_banque, nombre_joueur)
        await interaction.response.send_message(embed=embed, view=view)
        
        # On enregistre le message pour pouvoir l'éditer en cas de timeout (abandon)
        view.message = await interaction.original_response()

# ==============================================================================
# 💡 EXPLICATION DU SYSTÈME SÉCURISÉ
# ==============================================================================
# 1. 'update_money(user_id, -mise)' est appelé AVANT l'affichage des boutons.
# 2. 'on_timeout' est configuré pour que si le joueur ferme Discord ou ne répond pas,
#    le bot ne lui rende jamais son argent (C'est le risque du casino).
# 3. 'n_joueur' et 'n_banque' sont fixés avant le choix, empêchant toute triche 
#    par modification de code ou de variable pendant le délai de réflexion.
# 4. Le code est lié à ta base SQLite pour la persistance des gains.

# ==============================================================================
# 🚪 LE MYSTÈRE DES PORTES - ÉDITION GRAND CASINO (SÉCURISÉ & ANIMÉ)
# ==============================================================================

    @jeux.command(name="portes", description="🚪 Choisis la bonne porte pour multiplier ta mise !")
    async def portes(self, interaction: discord.Interaction, mise: int):
        """
        Jeu des Portes avec niveaux de difficulté et animations de révélation.
        Débit immédiat pour éviter les abandons.
        """
        user_id = interaction.user.id
        solde_actuel = self.get_user(user_id)

        # --- 1. VÉRIFICATIONS DE SÉCURITÉ ---
        erreur = self.check_mise(mise, 10, 50000, solde_actuel)
        if erreur:
            return await interaction.response.send_message(erreur, ephemeral=True)

        # --- 2. DÉBIT IMMÉDIAT (SÉCURITÉ ANTI-DECO) ---
        self.update_money(user_id, -mise)

        # --- 3. EMBED DE SÉLECTION DE DIFFICULTÉ ---
        embed_diff = discord.Embed(
            title="🚪 LE MYSTÈRE DES PORTES",
            description=(
                f"Bienvenue {interaction.user.mention} !\n"
                "Derrière une seule de ces portes se cache le **Trésor**.\n\n"
                "**Choisis ta difficulté :**\n"
                "🟢 **FACILE** : 3 Portes (Gain x2.5)\n"
                "🟡 **MOYEN** : 5 Portes (Gain x4.5)\n"
                "🔴 **DIFFICILE** : 10 Portes (Gain x9.0)"
            ),
            color=0x34495E # Bleu nuit
        )
        embed_diff.add_field(name="💰 Mise en jeu", value=f"`{self.fmt(mise)} €`")
        embed_diff.set_footer(text="Une fois la difficulté choisie, il n'y a plus de retour en arrière !")

        # --- 4. LOGIQUE DES BOUTONS DE DIFFICULTÉ ---
        class DifficulteView(discord.ui.View):
            def __init__(self, cog, user, mise_jouee):
                super().__init__(timeout=45)
                self.cog = cog
                self.user = user
                self.mise = mise_jouee
                self.choix_fait = False

            async def start_game(self, i: discord.Interaction, nb_portes, multiplicateur):
                if i.user.id != self.user.id:
                    return await i.response.send_message("❌ Ce n'est pas ton casino !", ephemeral=True)
                
                self.choix_fait = True
                bonne_porte = random.randint(1, nb_portes)
                
                # Passage à la vue du jeu
                game_view = PortesGameView(self.cog, self.user, self.mise, nb_portes, multiplicateur, bonne_porte)
                
                embed_game = discord.Embed(
                    title=f"🚪 JEU EN COURS - {nb_portes} PORTES",
                    description=f"Trouve la porte gagnante parmi les {nb_portes} propositions !\n\n*Bonne chance...*",
                    color=0xE67E22
                )
                embed_game.add_field(name="🎯 Multiplicateur", value=f"**x{multiplicateur}**")
                embed_game.add_field(name="💰 Gain potentiel", value=f"**{self.cog.fmt(int(self.mise * multiplicateur))} €**")

                await i.response.edit_message(embed=embed_game, view=game_view)
                game_view.message = await i.original_response()

            @discord.ui.button(label="FACILE", style=discord.ButtonStyle.success, emoji="🟢")
            async def facile(self, i, b): await self.start_game(i, 3, 2.5)

            @discord.ui.button(label="MOYEN", style=discord.ButtonStyle.primary, emoji="🟡")
            async def moyen(self, i, b): await self.start_game(i, 5, 4.5)

            @discord.ui.button(label="DIFFICILE", style=discord.ButtonStyle.danger, emoji="🔴")
            async def difficile(self, i, b): await self.start_game(i, 10, 9.0)

            async def on_timeout(self):
                if not self.choix_fait:
                    # Si timeout ici, la mise est déjà débitée donc perdue
                    try: await self.message.edit(content="❌ Temps écoulé pour choisir la difficulté. Mise perdue.", embed=None, view=None)
                    except: pass

        # --- 5. LOGIQUE DU JEU (CHOIX DE LA PORTE) ---
        class PortesGameView(discord.ui.View):
            def __init__(self, cog, user, mise, nb_portes, mult, bonne_porte):
                super().__init__(timeout=60)
                self.cog = cog
                self.user = user
                self.mise = mise
                self.nb_portes = nb_portes
                self.mult = mult
                self.bonne_porte = bonne_porte
                self.termine = False

                # Génération dynamique des boutons de portes
                for n in range(1, nb_portes + 1):
                    self.add_item(PorteButton(n))

            async def check_porte(self, i: discord.Interaction, numero_choisi):
                if i.user.id != self.user.id:
                    return await i.response.send_message("❌ Ce n'est pas ta partie !", ephemeral=True)
                
                if self.termine: return
                self.termine = True
                self.stop()

                # --- ANIMATION DE SUSPENSE ---
                for etape in ["🔍 Inspection...", "🔑 Ouverture...", "🚪 Craaaaac..."]:
                    embed_anim = discord.Embed(title=etape, color=0xF1C40F)
                    embed_anim.description = f"Tu as choisi la **Porte n°{numero_choisi}**.\nSuspense..."
                    await i.response.edit_message(embed=embed_anim, view=None) if not i.response.is_done() else await i.edit_original_response(embed=embed_anim, view=None)
                    await asyncio.sleep(0.8)

                # --- RÉSULTAT FINAL ---
                win = (numero_choisi == self.bonne_porte)
                final_embed = discord.Embed(timestamp=datetime.now())

                if win:
                    gain = int(self.mise * self.mult)
                    self.cog.update_money(self.user.id, gain)
                    final_embed.title = "🎊 INCROYABLE ! TU AS TROUVÉ LE TRÉSOR ! 🎊"
                    final_embed.color = 0x2ECC71
                    final_embed.description = (
                        f"La **Porte n°{numero_choisi}** était bien la bonne !\n\n"
                        f"💰 **Mise :** `{self.cog.fmt(self.mise)} €`\n"
                        f"📈 **Gain :** `+{self.cog.fmt(gain)} €`"
                    )
                    final_embed.set_image(url="https://i.imgur.com/vH3I0C8.gif") # Gif coffre au trésor
                else:
                    final_embed.title = "💀 MAUVAISE PORTE... 💀"
                    final_embed.color = 0xE74C3C
                    final_embed.description = (
                        f"Tu as ouvert la **Porte n°{numero_choisi}**...\n"
                        f"Elle était vide. Le trésor était derrière la **Porte n°{self.bonne_porte}**.\n\n"
                        f"❌ **Perte :** `-{self.cog.fmt(self.mise)} €`"
                    )
                
                nouveau_solde = self.cog.get_user(self.user.id)
                final_embed.add_field(name="💳 Nouveau Solde", value=f"**{self.cog.fmt(nouveau_solde)} €**")
                await i.edit_original_response(embed=final_embed, view=None)

            async def on_timeout(self):
                if not self.termine:
                    try: await self.message.edit(content="⏱️ Trop lent ! Le trésor a été déplacé. Mise perdue.", embed=None, view=None)
                    except: pass

        # --- 6. CLASSE POUR LES BOUTONS INDIVIDUELS ---
        class PorteButton(discord.ui.Button):
            def __init__(self, numero):
                super().__init__(
                    label=f"Porte {numero}",
                    style=discord.ButtonStyle.secondary,
                    emoji="🚪",
                    row=(numero-1)//5 # Répartit les boutons sur plusieurs lignes
                )
                self.numero = numero

            async def callback(self, i: discord.Interaction):
                await self.view.check_porte(i, self.numero)

        # --- 7. LANCEMENT ---
        view_diff = DifficulteView(self, interaction.user, mise)
        await interaction.response.send_message(embed=embed_diff, view=view_diff)
        view_diff.message = await interaction.original_response()

# ==============================================================================
# 💡 NOTES TECHNIQUES (SÉCURITÉ)
# ==============================================================================
# - L'argent est retiré à la ligne 25 (AVANT tout affichage).
# - Si l'utilisateur quitte après avoir choisi la difficulté, le casino garde l'argent.
# - Les gains (x2.5, x4.5, x9.0) sont calculés pour être rentables mais risqués.
# - Utilise self.bot.db pour assurer que les gains sont bien enregistrés sur Railway.

