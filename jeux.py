import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

class Jeux(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Configuration des IDs
        self.ID_ROLE_VIP = 1499809955841310871
        self.ID_CATEGORIE_CASINO = 1498394439079559318

    # --- LA BARRIÈRE DE SÉCURITÉ ---
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        user_role_ids = [role.id for role in interaction.user.roles]
        if self.ID_ROLE_VIP not in user_role_ids:
            await interaction.response.send_message("🚫 **Accès refusé** : Tu dois avoir le rôle VIP pour jouer aux jeux du Casino.", ephemeral=True)
            return False

        current_cat = getattr(interaction.channel, 'category_id', None)
        if current_cat != self.ID_CATEGORIE_CASINO:
            await interaction.response.send_message(f"🎰 **Mauvais salon** : Les jeux ne sont autorisés que dans la catégorie <#{self.ID_CATEGORIE_CASINO}>.", ephemeral=True)
            return False

        return True

    # --- TES FONCTIONS DE DONNÉES ---
    def get_user(self, user_id):
        """Récupère le solde du joueur dans SQLite (Départ 100€)"""
        cursor = self.bot.db.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, money, banque, last_daily, daily_streak) VALUES (?, ?, ?, ?, ?)", (user_id, 100, 0, 0, 0))
        self.bot.db.commit()
        cursor.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()[0]

    def update_money(self, user_id, amount):
        """Met à jour le solde (gain ou perte)"""
        cursor = self.bot.db.cursor()
        cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, user_id))
        self.bot.db.commit()

    def check_mise(self, mise, mini, maxi, solde):
        """Vérifie si la mise est valide"""
        if mise < mini: return f"❌ Mise minimale : `{self.fmt(mini)} €`."
        if mise > maxi: return f"❌ Mise maximale : `{self.fmt(maxi)} €`."
        if solde < mise: return f"❌ Solde insuffisant (Portefeuille : `{self.fmt(solde)} €`)."
        return None

    def fmt(self, n):
        return f"{n:,}".replace(",", " ")

    group = app_commands.Group(name="jeux", description="🎰 Casino Haute Tension")

@group.command(name="connecte4", description="🔴 Duel Puissance 4 contre un autre joueur")
    async def connecte4(self, interaction: discord.Interaction, adversaire: discord.Member, mise: int):
        if adversaire.id == interaction.user.id or adversaire.bot:
            return await interaction.response.send_message("❌ Action impossible.", ephemeral=True)

        u1_solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 1, 50000, u1_solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        u2_solde = self.get_user(adversaire.id)
        if u2_solde < mise:
            return await interaction.response.send_message(f"❌ **{adversaire.display_name}** n'a pas assez d'argent.", ephemeral=True)

        embed = discord.Embed(
            title="🔴 PUISSANCE 4 : DÉFI",
            description=f"{interaction.user.mention} défie {adversaire.mention} !\n💰 Mise : **{self.fmt(mise)} €**",
            color=0x3498DB # Bleu comme ton image
        )

        view = C4Invite(self, interaction.user, adversaire, mise)
        await interaction.response.send_message(content=adversaire.mention, embed=embed, view=view)

class C4Invite(discord.ui.View):
    def __init__(self, cog, p1, p2, mise):
        super().__init__(timeout=60)
        self.cog, self.p1, self.p2, self.mise = cog, p1, p2, mise

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success, emoji="✅")
    async def accept(self, i: discord.Interaction, b):
        if i.user.id != self.p2.id: return await i.response.send_message("❌ Ce n'est pas pour toi.", ephemeral=True)
        
        self.cog.update_money(self.p1.id, -self.mise)
        self.cog.update_money(self.p2.id, -self.mise)
        
        game = C4Game(self.cog, self.p1, self.p2, self.mise)
        await i.response.edit_message(content=None, embed=game.make_embed(), view=game)

    @discord.ui.button(label="Décliner", style=discord.ButtonStyle.danger, emoji="✖️")
    async def deny(self, i: discord.Interaction, b):
        if i.user.id != self.p2.id: return
        await i.response.edit_message(content="❌ Défi refusé.", embed=None, view=None)

class C4Game(discord.ui.View):
    def __init__(self, cog, p1, p2, mise):
        super().__init__(timeout=300)
        self.cog, self.p1, self.p2, self.mise = cog, p1, p2, mise
        # Grille : 6 lignes, 7 colonnes
        self.board = [[0 for _ in range(7)] for _ in range(6)]
        self.turn = p1
        self.symbols = {0: "⚪", 1: "🔴", 2: "🟡"}
        self.finished = False

    def make_embed(self):
        grid_text = ""
        for row in self.board:
            grid_text += "".join([self.symbols[cell] for cell in row]) + "\n"
        grid_text += "1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣" # Les chiffres sous les colonnes

        embed = discord.Embed(title="🎮 MATCH EN COURS", color=0x3498DB)
        embed.description = (
            f"🔴 {self.p1.mention} vs 🟡 {self.p2.mention}\n\n"
            f"{grid_text}\n\n"
            f"Tour de : **{self.turn.display_name}**"
        )
        return embed

    def check_win(self, p):
        # Horizontal
        for r in range(6):
            for c in range(4):
                if self.board[r][c] == p and self.board[r][c+1] == p and self.board[r][c+2] == p and self.board[r][c+3] == p: return True
        # Vertical
        for r in range(3):
            for c in range(7):
                if self.board[r][c] == p and self.board[r+1][c] == p and self.board[r+2][c] == p and self.board[r+3][c] == p: return True
        # Diagonal /
        for r in range(3, 6):
            for c in range(4):
                if self.board[r][c] == p and self.board[r-1][c+1] == p and self.board[r-2][c+2] == p and self.board[r-3][c+3] == p: return True
        # Diagonal \
        for r in range(3):
            for c in range(4):
                if self.board[r][c] == p and self.board[r+1][c+1] == p and self.board[r+2][c+2] == p and self.board[r+3][c+3] == p: return True
        return False

    async def play(self, i, col):
        if i.user.id != self.turn.id:
            return await i.response.send_message("❌ Ce n'est pas ton tour !", ephemeral=True)

        # Placer le jeton (cherche la ligne vide la plus basse)
        placed = False
        p_val = 1 if i.user == self.p1 else 2
        for r in range(5, -1, -1):
            if self.board[r][col] == 0:
                self.board[r][col] = p_val
                placed = True
                break
        
        if not placed:
            return await i.response.send_message("❌ Cette colonne est pleine !", ephemeral=True)

        # Vérification victoire
        if self.check_win(p_val):
            self.finished = True
            gain = self.mise * 2
            self.cog.update_money(i.user.id, gain)
            emb = self.make_embed()
            emb.title = "🏆 VICTOIRE !"
            emb.description = f"🔥 {i.user.mention} a gagné **{self.cog.fmt(gain)} €** !\n\n" + emb.description.split("\n\n")[1]
            return await i.response.edit_message(embed=emb, view=None)

        # Tour suivant
        self.turn = self.p2 if self.turn == self.p1 else self.p1
        await i.response.edit_message(embed=self.make_embed(), view=self)

    # Boutons de 1 à 7 (Bleus comme sur l'image)
    @discord.ui.button(label="1", style=discord.ButtonStyle.blurple)
    async def c1(self, i, b): await self.play(i, 0)
    @discord.ui.button(label="2", style=discord.ButtonStyle.blurple)
    async def c2(self, i, b): await self.play(i, 1)
    @discord.ui.button(label="3", style=discord.ButtonStyle.blurple)
    async def c3(self, i, b): await self.play(i, 2)
    @discord.ui.button(label="4", style=discord.ButtonStyle.blurple)
    async def c4(self, i, b): await self.play(i, 3)
    @discord.ui.button(label="5", style=discord.ButtonStyle.blurple)
    async def c5(self, i, b): await self.play(i, 4)
    @discord.ui.button(label="6", style=discord.ButtonStyle.blurple)
    async def c6(self, i, b): await self.play(i, 5)
    @discord.ui.button(label="7", style=discord.ButtonStyle.blurple)
    async def c7(self, i, b): await self.play(i, 6)

@group.command(name="course", description="🏇 Course multijoueur (2-6 pers) : Le gagnant rafle toute la mise !")
    async def course(self, interaction: discord.Interaction, mise: int):
        solde_host = self.get_user(interaction.user.id)
        if mise < 50: return await interaction.response.send_message("❌ La mise minimale est de 50 €.", ephemeral=True)
        if solde_host < mise: return await interaction.response.send_message("❌ Tu n'as pas assez d'argent pour organiser cette course.", ephemeral=True)

        # --- ACTION : L'hôte paie sa place immédiatement ---
        self.update_money(interaction.user.id, -mise)

        embed = discord.Embed(
            title="🏇 GRANDE COURSE HIPPIQUE",
            description=(
                f"**{interaction.user.display_name}** organise une course !\n"
                f"💰 Mise par personne : **{self.fmt(mise)} €**\n\n"
                f"**Inscrits (1/6) :**\n• {interaction.user.display_name}"
            ),
            color=0x27ae60
        )
        embed.set_footer(text="L'organisateur doit lancer la course quand tout le monde est prêt.")

        class CourseView(discord.ui.View):
            def __init__(self, cog, host, mise):
                super().__init__(timeout=120) # 2 minutes pour recruter
                self.cog = cog
                self.participants = [host]
                self.mise = mise
                self.started = False

            async def on_timeout(self):
                if not self.started:
                    # REMBOURSEMENT si la course n'a pas commencé
                    for p in self.participants:
                        self.cog.update_money(p.id, self.mise)

            @discord.ui.button(label="Participer", emoji="🏇", style=discord.ButtonStyle.green)
            async def join(self, i: discord.Interaction, b: discord.ui.Button):
                if self.started: return await i.response.send_message("❌ La course a déjà commencé !", ephemeral=True)
                if i.user.id in [p.id for p in self.participants]: return await i.response.send_message("❌ Tu es déjà sur ton cheval !", ephemeral=True)
                if len(self.participants) >= 6: return await i.response.send_message("❌ L'écurie est complète (6/6) !", ephemeral=True)
                
                s = self.cog.get_user(i.user.id)
                if s < self.mise: return await i.response.send_message("❌ Tu n'as pas les fonds pour miser.", ephemeral=True)

                # --- ACTION : Le participant paie immédiatement ---
                self.cog.update_money(i.user.id, -self.mise)
                self.participants.append(i.user)
                
                n = len(self.participants)
                emb = i.message.embeds[0]
                emb.description = f"**Organisateur :** {self.participants[0].display_name}\n💰 Mise : **{self.cog.fmt(self.mise)} €**\n\n**Inscrits ({n}/6) :**\n" + "\n".join([f"• {p.display_name}" for p in self.participants])
                await i.response.edit_message(embed=emb, view=self)

            @discord.ui.button(label="Lancer !", emoji="🚩", style=discord.ButtonStyle.blurple)
            async def start(self, i: discord.Interaction, b: discord.ui.Button):
                if i.user.id != self.participants[0].id: return await i.response.send_message("❌ Seul l'organisateur peut donner le départ.", ephemeral=True)
                if len(self.participants) < 2: return await i.response.send_message("❌ Il faut au moins 2 coureurs pour lancer !", ephemeral=True)
                
                self.started = True
                self.clear_items()
                await i.response.edit_message(content="🚦 **PRÊTS ? LES PORTES S'OUVRENT !**", view=self)

                # Animation stylée
                pistes = {p.display_name: 0 for p in self.participants}
                for _ in range(4):
                    await asyncio.sleep(1.5)
                    for p in pistes: pistes[p] += random.randint(1, 4)
                    progression = "\n".join([f"🏇 | {'—' * pistes[p]} **{p}**" for p in pistes])
                    await i.edit_original_response(content=f"🏁 **LA COURSE BAT SON PLEIN !**\n\n{progression}")

                # Résultat
                gagnant = random.choice(self.participants)
                cagnotte = self.mise * len(self.participants)
                
                # --- ACTION : On donne la cagnotte au gagnant ---
                self.cog.update_money(gagnant.id, cagnotte)

                res = discord.Embed(
                    title="🏆 RÉSULTAT DE LA COURSE",
                    description=(
                        f"Photo-finish incroyable ! 📸\n\n"
                        f"Le cheval de **{gagnant.mention}** gagne d'une courte tête !\n"
                        f"💰 Il repart avec la cagnotte de **{self.cog.fmt(cagnotte)} €** !"
                    ),
                    color=0xF1C40F
                )
                await i.edit_original_response(content=None, embed=res)

            @discord.ui.button(label="Annuler", emoji="🚫", style=discord.ButtonStyle.secondary)
            async def cancel(self, i: discord.Interaction, b: discord.ui.Button):
                if i.user.id != self.participants[0].id: return await i.response.send_message("❌ Seul l'organisateur peut annuler.", ephemeral=True)
                self.started = True # Pour stopper le timeout
                for p in self.participants:
                    self.cog.update_money(p.id, self.mise)
                await i.response.edit_message(content="❌ Course annulée. Tout le monde a été remboursé.", embed=None, view=None)

        await interaction.response.send_message(embed=embed, view=CourseView(self, interaction.user, mise))

@group.command(name="mystere", description="🔢 Devine si ton nombre sera plus haut ou plus bas (1-14)")
    async def mystere(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(pari, 1, 2500, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        # --- ACTION : On retire la mise DIRECTEMENT ---
        self.update_money(interaction.user.id, -pari)

        # On génère les nombres (Banque et Joueur)
        bc = random.randint(1, 14)
        uc = random.randint(1, 14)
        # Sécurité : On s'assure que uc != bc pour éviter les égalités frustrantes au début
        while uc == bc:
            uc = random.randint(1, 14)

        embed = discord.Embed(
            title="🔢 JEU DU MYSTÈRE",
            description=(
                f"La banque a tiré le nombre : **{bc}**\n\n"
                f"Ton nombre est caché... 🕵️‍♂️\n"
                f"Sera-t-il **plus haut** ou **plus bas** que celui de la banque ?"
            ),
            color=0x3498DB
        )
        embed.set_footer(text="Fais ton choix avec les boutons ci-dessous !")
        embed.add_field(name="💰 Mise", value=f"**{self.fmt(pari)} €**", inline=True)
        embed.add_field(name="📈 Multiplicateur", value="**x2.0**", inline=True)

        class MystereView(discord.ui.View):
            def __init__(self, cog, bc, uc, pari, user):
                super().__init__(timeout=30)
                self.cog, self.bc, self.uc, self.pari, self.user = cog, bc, uc, pari, user

            async def on_timeout(self):
                # Si le temps expire, le pari est déjà perdu car retiré au début.
                pass

            async def process_choice(self, i: discord.Interaction, choice: str):
                if i.user.id != self.user.id: 
                    return await i.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)

                res_embed = discord.Embed(title="🔢 RÉSULTAT DU MYSTÈRE")
                res_embed.add_field(name="Banque", value=f"**{self.bc}**", inline=True)
                res_embed.add_field(name="Toi", value=f"**{self.uc}**", inline=True)
                
                # Logique de victoire
                win = (choice == "h" and self.uc > self.bc) or (choice == "b" and self.uc < self.bc)

                if win:
                    gain = self.pari * 2 # On rend la mise + le gain (x2)
                    self.cog.update_money(i.user.id, gain)
                    res_embed.color = 0x2ECC71
                    res_embed.description = f"### ✅ VICTOIRE !\nC'est passé ! Tu remportes **{self.cog.fmt(gain)} €**."
                else:
                    res_embed.color = 0xE74C3C
                    res_embed.description = f"### 💀 PERDU\nMauvais pronostic... Tu perds ta mise de **{self.cog.fmt(self.pari)} €**."

                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="PLUS HAUT", emoji="⏫", style=discord.ButtonStyle.success)
            async def plus_haut(self, i, b): await self.process_choice(i, "h")

            @discord.ui.button(label="PLUS BAS", emoji="⏬", style=discord.ButtonStyle.danger)
            async def plus_bas(self, i, b): await self.process_choice(i, "b")

        await interaction.response.send_message(embed=embed, view=MystereView(self, bc, uc, pari, interaction.user))

@group.command(name="pfc", description="⚔️ Duel en 3 manches (BO3) ! Le premier à 2 victoires rafle tout.")
    async def pfc(self, interaction: discord.Interaction, adversaire: discord.Member, mise: int):
        if adversaire.id == interaction.user.id or adversaire.bot:
            return await interaction.response.send_message("❌ Impossible de se battre soi-même ou un bot.", ephemeral=True)

        u1_s, u2_s = self.get_user(interaction.user.id), self.get_user(adversaire.id)
        err = self.check_mise(mise, 100, 20000, u1_s)
        if err: return await interaction.response.send_message(err, ephemeral=True)
        if u2_s < mise: return await interaction.response.send_message(f"❌ {adversaire.mention} est trop pauvre pour ce duel.", ephemeral=True)

        embed = discord.Embed(
            title="⚔️ DÉFI DE DUEL (BO3)", 
            description=f"{interaction.user.mention} veut t'affronter au PFC !\n💰 Enjeu total : **{self.fmt(mise*2)} €**\n\n*Le premier à 2 points gagne la cagnotte.*", 
            color=0xF1C40F
        )

        class PFCInvite(discord.ui.View):
            def __init__(self, cog, p1, p2, mise):
                super().__init__(timeout=60)
                self.cog, self.p1, self.p2, self.mise = cog, p1, p2, mise

            @discord.ui.button(label="ACCEPTER", emoji="⚔️", style=discord.ButtonStyle.success)
            async def accept(self, i: discord.Interaction, b):
                if i.user.id != self.p2.id: return await i.response.send_message("❌ Ce n'est pas pour toi.", ephemeral=True)
                
                # Prélèvement des deux joueurs
                self.cog.update_money(self.p1.id, -self.mise)
                self.cog.update_money(self.p2.id, -self.mise)
                
                game = PFCGame(self.cog, self.p1, self.p2, self.mise)
                await i.response.edit_message(content=None, embed=game.make_embed(), view=game)

            @discord.ui.button(label="REFUSER", emoji="🚫", style=discord.ButtonStyle.danger)
            async def deny(self, i: discord.Interaction, b):
                if i.user.id != self.p2.id: return await i.response.send_message("❌ Ce n'est pas pour toi.", ephemeral=True)
                await i.response.edit_message(content="🛡️ Duel décliné.", embed=None, view=None)

        class PFCGame(discord.ui.View):
            def __init__(self, cog, p1, p2, mise):
                super().__init__(timeout=120)
                self.cog, self.p1, self.p2, self.mise = cog, p1, p2, mise
                self.scores = {p1.id: 0, p2.id: 0}
                self.choices = {p1.id: None, p2.id: None}
                self.manche = 1
                self.logs = "En attente des choix..."
                self.emojis = {"pierre": "🪨", "feuille": "🍃", "ciseaux": "✂️"}

            def make_embed(self):
                embed = discord.Embed(title=f"⚔️ DUEL : MANCHE {self.manche}", color=0x5865F2)
                embed.add_field(name=f"🔴 {self.p1.display_name}", value=f"Score : **{self.scores[self.p1.id]}**", inline=True)
                embed.add_field(name=f"🟡 {self.p2.display_name}", value=f"Score : **{self.scores[self.p2.id]}**", inline=True)
                
                status_p1 = "✅ PRÊT" if self.choices[self.p1.id] else "⏳ CHOISIT..."
                status_p2 = "✅ PRÊT" if self.choices[self.p2.id] else "⏳ CHOISIT..."
                
                embed.add_field(name="État des joueurs", value=f"{self.p1.mention} : {status_p1}\n{self.p2.mention} : {status_p2}", inline=False)
                embed.add_field(name="Dernier round", value=self.logs, inline=False)
                embed.set_footer(text="Premier à 2 points ! En cas d'égalité, on rejoue la manche.")
                return embed

            async def check_round(self, i):
                c1, c2 = self.choices[self.p1.id], self.choices[self.p2.id]
                if c1 and c2:
                    win_map = {"pierre": "ciseaux", "feuille": "pierre", "ciseaux": "feuille"}
                    
                    if c1 == c2:
                        self.logs = f"🤝 Égalité (**{self.emojis[c1]}**)! On refait la manche {self.manche}."
                    elif win_map[c1] == c2:
                        self.scores[self.p1.id] += 1
                        self.logs = f"✅ **{self.p1.display_name}** gagne la manche ({self.emojis[c1]} bat {self.emojis[c2]})"
                        self.manche += 1
                    else:
                        self.scores[self.p2.id] += 1
                        self.logs = f"✅ **{self.p2.display_name}** gagne la manche ({self.emojis[c2]} bat {self.emojis[c1]})"
                        self.manche += 1

                    # Reset des choix pour la suite
                    self.choices[self.p1.id] = None
                    self.choices[self.p2.id] = None

                    # Vérif si un gagnant final
                    if self.scores[self.p1.id] == 2 or self.scores[self.p2.id] == 2:
                        winner = self.p1 if self.scores[self.p1.id] == 2 else self.p2
                        gain = self.mise * 2
                        self.cog.update_money(winner.id, gain)
                        
                        final_emb = discord.Embed(title="🏆 VICTOIRE FINALE !", description=f"{winner.mention} remporte le duel **{max(self.scores.values())} - {min(self.scores.values())}** !\n💰 Gain : **{self.cog.fmt(gain)} €**", color=0x2ECC71)
                        return await i.edit_original_response(embed=final_emb, view=None)

                    await i.edit_original_response(embed=self.make_embed())

            async def handle_play(self, i, choice):
                if i.user.id not in [self.p1.id, self.p2.id]: 
                    return await i.response.send_message("❌ Tu ne joues pas !", ephemeral=True)
                if self.choices[i.user.id]: 
                    return await i.response.send_message("✅ Tu as déjà fait ton choix, attends l'autre !", ephemeral=True)
                
                self.choices[i.user.id] = choice
                await i.response.send_message(f"Tu as joué {self.emojis[choice]} ! Chut, c'est secret...", ephemeral=True)
                await self.check_round(i)

            @discord.ui.button(label="Pierre", emoji="🪨", style=discord.ButtonStyle.secondary)
            async def rock(self, i, b): await self.handle_play(i, "pierre")
            @discord.ui.button(label="Feuille", emoji="🍃", style=discord.ButtonStyle.secondary)
            async def paper(self, i, b): await self.handle_play(i, "feuille")
            @discord.ui.button(label="Ciseaux", emoji="✂️", style=discord.ButtonStyle.secondary)
            async def scissors(self, i, b): await self.handle_play(i, "ciseaux")

        await interaction.response.send_message(embed=embed, view=PFCInvite(self, interaction.user, adversaire, mise))

@group.command(name="pileouface", description="🪙 Tente de doubler ta mise sur un lancer de pièce !")
    async def pileouface(self, interaction: discord.Interaction, pari: int):
        # --- VÉRIFICATIONS ---
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(pari, 10, 10000, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        # --- ACTION : On retire la mise DIRECTEMENT ---
        self.update_money(interaction.user.id, -pari)

        # On prépare l'embed de choix
        embed = discord.Embed(
            title="🪙 PILE OU FACE",
            description=f"Mise : **{self.fmt(pari)} €**\n\nFais ton choix en cliquant sur un bouton !",
            color=0xF1C40F
        )
        
        # --- LA VUE AVEC LES BOUTONS ---
        class PFView(discord.ui.View):
            def __init__(self, cog, user, pari):
                super().__init__(timeout=60)
                self.cog, self.user, self.pari = cog, user, pari

            async def jouer(self, i, choix):
                if i.user.id != self.user.id: return
                
                # Désactive les boutons après le clic
                for b in self.children: b.disabled = True
                
                # Animation
                await i.response.edit_message(content="🪙 *La pièce tourne...*", embed=None, view=self)
                await asyncio.sleep(2)
                
                # Résultat
                resultat = random.choice(["pile", "face"])
                win = (choix == resultat)
                
                res_embed = discord.Embed(title="🪙 RÉSULTAT")
                if win:
                    gain = self.pari * 2
                    self.cog.update_money(self.user.id, gain)
                    res_embed.color = 0x2ECC71
                    res_embed.description = f"### ✅ C'EST {resultat.upper()} !\n\nBravo ! Tu remportes **{self.cog.fmt(gain)} €** !"
                else:
                    res_embed.color = 0xE74C3C
                    res_embed.description = f"### 💀 C'EST {resultat.upper()}...\n\nPerdu ! Tu perds ta mise de **{self.cog.fmt(self.pari)} €**."
                
                await i.edit_original_response(content=None, embed=res_embed, view=None)

            @discord.ui.button(label="PILE", style=discord.ButtonStyle.primary, emoji="🪙")
            async def pile(self, i, b): await self.jouer(i, "pile")

            @discord.ui.button(label="FACE", style=discord.ButtonStyle.secondary, emoji="👤")
            async def face(self, i, b): await self.jouer(i, "face")

        await interaction.response.send_message(embed=embed, view=PFView(self, interaction.user, pari))

@group.command(name="portes", description="🚪 Tente de trouver le trésor derrière l'une des 3 portes")
    async def portes(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(pari, 1, 10000, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        # --- ACTION : On retire la mise DIRECTEMENT ---
        self.update_money(interaction.user.id, -pari)

        win_door = random.randint(1, 3)
        
        embed = discord.Embed(
            title="🚪 LE JEU DES PORTES", 
            description=(
                "Le trésor est caché derrière l'une de ces trois portes...\n"
                "**Fais le bon choix !** 🍀"
            ), 
            color=0x9B59B6
        )
        embed.add_field(name="💰 Mise engagée", value=f"**{self.fmt(pari)} €**", inline=True)
        embed.add_field(name="🏆 Jackpot", value=f"**{self.fmt(pari*3)} €** (x3)", inline=True)
        embed.set_footer(text="Une seule porte contient l'or, les autres sont vides.")

        class PortesView(discord.ui.View):
            def __init__(self, cog, win_door, pari, user):
                super().__init__(timeout=30)
                self.cog, self.win_door, self.pari, self.user = cog, win_door, pari, user

            async def play(self, i: discord.Interaction, choice: int):
                if i.user.id != self.user.id: 
                    return await i.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)

                # Construction du résultat visuel
                reveil = ""
                for n in range(1, 4):
                    if n == self.win_door:
                        reveil += f"Porte {n} : 💰 **TRÉSOR**"
                    else:
                        reveil += f"Porte {n} : 💨 **VIDE**"
                    
                    if choice == n:
                        reveil += " 👈 (Ton choix)"
                    reveil += "\n"

                res_embed = discord.Embed(description=reveil)

                if choice == self.win_door:
                    # VICTOIRE : On donne le x3 (Puisqu'on a déjà retiré le pari au début)
                    gain = self.pari * 3
                    self.cog.update_money(i.user.id, gain)
                    res_embed.title = "✨ INCROYABLE VICTOIRE !"
                    res_embed.color = 0xF1C40F
                    res_embed.add_field(name="Bilan", value=f"Tu as trouvé l'or ! Gain : **+{self.cog.fmt(gain)} €**")
                else:
                    # DÉFAITE : L'argent est déjà perdu (retiré au début)
                    res_embed.title = "💨 C'EST VIDE..."
                    res_embed.color = 0xE74C3C
                    res_embed.add_field(name="Bilan", value=f"Pas de chance ! Perte : **-{self.cog.fmt(self.pari)} €**")

                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="PORTE 1", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b1(self, i, b): await self.play(i, 1)
            @discord.ui.button(label="PORTE 2", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b2(self, i, b): await self.play(i, 2)
            @discord.ui.button(label="PORTE 3", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b3(self, i, b): await self.play(i, 3)

        await interaction.response.send_message(embed=embed, view=PortesView(self, win_door, pari, interaction.user))



# --- TRUCS DE FIN ---
async def setup(bot):
    await bot.add_cog(Jeux(bot))
