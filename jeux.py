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



# --- TRUCS DE FIN ---
async def setup(bot):
    await bot.add_cog(Jeux(bot))
