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

# =========================
# 🔴 PUISSANCE 4 COMPLET
# =========================

@group.command(name="connecte4", description="🔴 Duel Puissance 4 contre un autre joueur")
async def connecte4(self, interaction: discord.Interaction, adversaire: discord.Member, mise: int):
    if adversaire.id == interaction.user.id or adversaire.bot:
        return await interaction.response.send_message("❌ Action impossible.", ephemeral=True)

    u1_solde = self.get_user(interaction.user.id)
    err = self.check_mise(mise, 1, 50000, u1_solde)
    if err:
        return await interaction.response.send_message(err, ephemeral=True)

    u2_solde = self.get_user(adversaire.id)
    if u2_solde < mise:
        return await interaction.response.send_message(f"❌ {adversaire.display_name} n'a pas assez d'argent.", ephemeral=True)

    embed = discord.Embed(
        title="🔴 PUISSANCE 4 : DÉFI",
        description=f"{interaction.user.mention} défie {adversaire.mention}\n💰 Mise : **{self.fmt(mise)} €**",
        color=0x3498DB
    )

    await interaction.response.send_message(
        content=adversaire.mention,
        embed=embed,
        view=C4Invite(self, interaction.user, adversaire, mise)
    )


class C4Invite(discord.ui.View):
    def __init__(self, cog, p1, p2, mise):
        super().__init__(timeout=60)
        self.cog, self.p1, self.p2, self.mise = cog, p1, p2, mise

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success)
    async def accept(self, i: discord.Interaction, b):
        if i.user.id != self.p2.id:
            return await i.response.send_message("❌ Pas pour toi.", ephemeral=True)

        self.cog.update_money(self.p1.id, -self.mise)
        self.cog.update_money(self.p2.id, -self.mise)

        game = C4Game(self.cog, self.p1, self.p2, self.mise)
        await i.response.edit_message(embed=game.make_embed(), view=game)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def deny(self, i: discord.Interaction, b):
        if i.user.id != self.p2.id:
            return
        await i.response.edit_message(content="❌ Défi refusé.", embed=None, view=None)


class C4Game(discord.ui.View):
    def __init__(self, cog, p1, p2, mise):
        super().__init__(timeout=300)
        self.cog, self.p1, self.p2, self.mise = cog, p1, p2, mise
        self.board = [[0 for _ in range(7)] for _ in range(6)]
        self.turn = p1
        self.symbols = {0: "⚪", 1: "🔴", 2: "🟡"}
        self.finished = False

    def make_embed(self):
        grid = ""

        for row in reversed(self.board):
            grid += " ".join([self.symbols[cell] for cell in row]) + "\n"

        grid += "\n1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣"

        embed = discord.Embed(title="🎮 MATCH EN COURS", color=0x3498DB)
        embed.description = (
            f"🔴 {self.p1.mention} vs 🟡 {self.p2.mention}\n\n"
            f"{grid}\n\n"
            f"Tour de : **{self.turn.display_name}**"
        )
        return embed

    def check_win(self, p):
        # Horizontal
        for r in range(6):
            for c in range(4):
                if all(self.board[r][c+i] == p for i in range(4)):
                    return True

        # Vertical
        for r in range(3):
            for c in range(7):
                if all(self.board[r+i][c] == p for i in range(4)):
                    return True

        # Diagonale /
        for r in range(3, 6):
            for c in range(4):
                if all(self.board[r-i][c+i] == p for i in range(4)):
                    return True

        # Diagonale \
        for r in range(3):
            for c in range(4):
                if all(self.board[r+i][c+i] == p for i in range(4)):
                    return True

        return False

    def is_full(self):
        return all(self.board[0][c] != 0 for c in range(7))

    async def play(self, i, col):
        if self.finished:
            return

        if i.user.id != self.turn.id:
            return await i.response.send_message("❌ Pas ton tour", ephemeral=True)

        p_val = 1 if i.user == self.p1 else 2

        for r in range(5, -1, -1):
            if self.board[r][col] == 0:
                self.board[r][col] = p_val
                break
        else:
            return await i.response.send_message("❌ Colonne pleine", ephemeral=True)

        # victoire
        if self.check_win(p_val):
            self.finished = True
            self.clear_items()

            gain = self.mise * 2
            self.cog.update_money(i.user.id, gain)

            emb = self.make_embed()
            emb.title = "🏆 VICTOIRE"
            emb.description = f"{i.user.mention} gagne **{self.cog.fmt(gain)} €**\n\n" + emb.description.split("\n\n")[1]

            return await i.response.edit_message(embed=emb, view=None)

        # match nul
        if self.is_full():
            self.finished = True
            self.clear_items()

            self.cog.update_money(self.p1.id, self.mise)
            self.cog.update_money(self.p2.id, self.mise)

            emb = self.make_embed()
            emb.title = "🤝 MATCH NUL"
            emb.description = "La grille est pleine ! Remboursement."

            return await i.response.edit_message(embed=emb, view=None)

        # changement de tour
        self.turn = self.p2 if self.turn == self.p1 else self.p1
        await i.response.edit_message(embed=self.make_embed(), view=self)

    # boutons
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

# =========================
# 🏇 COURSE COMPLETE
# =========================

@group.command(name="course", description="🏇 Course multijoueur (2-6 pers)")
async def course(self, interaction: discord.Interaction, mise: int):
    solde_host = self.get_user(interaction.user.id)

    if mise < 50:
        return await interaction.response.send_message("❌ Mise minimale : 50 €", ephemeral=True)

    if solde_host < mise:
        return await interaction.response.send_message("❌ Pas assez d'argent.", ephemeral=True)

    # Paiement de l'hôte
    self.update_money(interaction.user.id, -mise)

    embed = discord.Embed(
        title="🏇 COURSE HIPPIQUE",
        description=(
            f"Organisateur : {interaction.user.mention}\n"
            f"Mise : **{self.fmt(mise)} €**\n\n"
            f"**Participants (1/6)**\n• {interaction.user.display_name}"
        ),
        color=0x27ae60
    )

    class CourseView(discord.ui.View):
        def __init__(self, cog, host, mise):
            super().__init__(timeout=120)
            self.cog = cog
            self.mise = mise
            self.participants = [host]
            self.started = False

        async def on_timeout(self):
            if not self.started:
                for p in self.participants:
                    self.cog.update_money(p.id, self.mise)
                self.clear_items()

        @discord.ui.button(label="Participer", emoji="🏇", style=discord.ButtonStyle.green)
        async def join(self, i: discord.Interaction, b):
            if self.started:
                return await i.response.send_message("❌ Déjà lancé.", ephemeral=True)

            if i.user.id in [p.id for p in self.participants]:
                return await i.response.send_message("❌ Déjà inscrit.", ephemeral=True)

            if len(self.participants) >= 6:
                return await i.response.send_message("❌ Complet (6/6).", ephemeral=True)

            solde = self.cog.get_user(i.user.id)
            if solde < self.mise:
                return await i.response.send_message("❌ Pas assez d'argent.", ephemeral=True)

            self.cog.update_money(i.user.id, -self.mise)
            self.participants.append(i.user)

            emb = i.message.embeds[0]
            emb.description = (
                f"Organisateur : {self.participants[0].mention}\n"
                f"Mise : **{self.cog.fmt(self.mise)} €**\n\n"
                f"**Participants ({len(self.participants)}/6)**\n"
                + "\n".join([f"• {p.display_name}" for p in self.participants])
            )

            await i.response.edit_message(embed=emb, view=self)

        @discord.ui.button(label="Lancer", emoji="🚩", style=discord.ButtonStyle.blurple)
        async def start(self, i: discord.Interaction, b):
            if i.user.id != self.participants[0].id:
                return await i.response.send_message("❌ Seul l'organisateur peut lancer.", ephemeral=True)

            if len(self.participants) < 2:
                return await i.response.send_message("❌ Minimum 2 joueurs.", ephemeral=True)

            self.started = True
            self.clear_items()

            await i.response.edit_message(content="🚦 La course commence !", view=None)

            pistes = {p.display_name: 0 for p in self.participants}

            for _ in range(5):
                await asyncio.sleep(1.5)

                for p in pistes:
                    pistes[p] += random.randint(1, 3)

                txt = "\n".join([
                    f"🏇 {'—' * pistes[p]} {p}"
                    for p in pistes
                ])

                await i.edit_original_response(content=f"🏁 COURSE EN COURS\n\n{txt}")

            gagnant = max(pistes, key=pistes.get)
            gagnant_user = next(p for p in self.participants if p.display_name == gagnant)

            cagnotte = self.mise * len(self.participants)
            self.cog.update_money(gagnant_user.id, cagnotte)

            embed = discord.Embed(
                title="🏆 RÉSULTAT",
                description=(
                    f"Le gagnant est {gagnant_user.mention} !\n"
                    f"💰 Gain : **{self.cog.fmt(cagnotte)} €**"
                ),
                color=0xF1C40F
            )

            await i.edit_original_response(content=None, embed=embed)

        @discord.ui.button(label="Annuler", emoji="🚫", style=discord.ButtonStyle.gray)
        async def cancel(self, i: discord.Interaction, b):
            if i.user.id != self.participants[0].id:
                return await i.response.send_message("❌ Seul l'organisateur peut annuler.", ephemeral=True)

            self.started = True

            for p in self.participants:
                self.cog.update_money(p.id, self.mise)

            self.clear_items()

            await i.response.edit_message(
                content="❌ Course annulée. Remboursement effectué.",
                embed=None,
                view=None
            )

    await interaction.response.send_message(
        embed=embed,
        view=CourseView(self, interaction.user, mise)
            )

# =========================
# 🔢 JEU MYSTÈRE COMPLET
# =========================

@group.command(name="mystere", description="🔢 Devine si ton nombre sera plus haut ou plus bas (1-14)")
async def mystere(self, interaction: discord.Interaction, pari: int):
    solde = self.get_user(interaction.user.id)

    err = self.check_mise(pari, 1, 2500, solde)
    if err:
        return await interaction.response.send_message(err, ephemeral=True)

    # retrait immédiat
    self.update_money(interaction.user.id, -pari)

    # génération nombres
    bc = random.randint(1, 14)
    uc = random.randint(1, 14)

    while uc == bc:
        uc = random.randint(1, 14)

    embed = discord.Embed(
        title="🔢 JEU DU MYSTÈRE",
        description=(
            f"La banque a tiré : **{bc}**\n\n"
            f"Ton nombre est caché...\n"
            f"Est-il **plus haut** ou **plus bas** ?"
        ),
        color=0x3498DB
    )

    embed.add_field(name="💰 Mise", value=f"{self.fmt(pari)} €")
    embed.add_field(name="📈 Gain possible", value=f"{self.fmt(pari*2)} €")

    class MystereView(discord.ui.View):
        def __init__(self, cog, bc, uc, pari, user):
            super().__init__(timeout=30)
            self.cog = cog
            self.bc = bc
            self.uc = uc
            self.pari = pari
            self.user = user
            self.played = False

        async def on_timeout(self):
            if not self.played:
                self.clear_items()

        async def process(self, i: discord.Interaction, choix: str):
            if self.played:
                return

            if i.user.id != self.user.id:
                return await i.response.send_message("❌ Ce n'est pas ton jeu.", ephemeral=True)

            self.played = True
            self.clear_items()

            # victoire ?
            win = (choix == "haut" and self.uc > self.bc) or (choix == "bas" and self.uc < self.bc)

            res = discord.Embed(title="🔢 RÉSULTAT")

            res.add_field(name="Banque", value=str(self.bc), inline=True)
            res.add_field(name="Toi", value=str(self.uc), inline=True)

            if win:
                gain = self.pari * 2
                self.cog.update_money(self.user.id, gain)

                res.color = 0x2ECC71
                res.description = f"✅ GAGNÉ ! Tu remportes **{self.cog.fmt(gain)} €**"
            else:
                res.color = 0xE74C3C
                res.description = f"💀 PERDU ! Tu perds **{self.cog.fmt(self.pari)} €**"

            await i.response.edit_message(embed=res, view=None)

        @discord.ui.button(label="PLUS HAUT", emoji="⏫", style=discord.ButtonStyle.success)
        async def haut(self, i, b):
            await self.process(i, "haut")

        @discord.ui.button(label="PLUS BAS", emoji="⏬", style=discord.ButtonStyle.danger)
        async def bas(self, i, b):
            await self.process(i, "bas")

    await interaction.response.send_message(
        embed=embed,
        view=MystereView(self, bc, uc, pari, interaction.user)
            )

# =========================
# ⚔️ PFC COMPLET
# =========================

@group.command(name="pfc", description="⚔️ Duel en BO3")
async def pfc(self, interaction: discord.Interaction, adversaire: discord.Member, mise: int):
    if adversaire.id == interaction.user.id or adversaire.bot:
        return await interaction.response.send_message("❌ Impossible.", ephemeral=True)

    u1 = self.get_user(interaction.user.id)
    u2 = self.get_user(adversaire.id)

    err = self.check_mise(mise, 100, 20000, u1)
    if err:
        return await interaction.response.send_message(err, ephemeral=True)

    if u2 < mise:
        return await interaction.response.send_message("❌ L'adversaire n'a pas assez.", ephemeral=True)

    embed = discord.Embed(
        title="⚔️ Duel PFC",
        description=f"{interaction.user.mention} vs {adversaire.mention}\n💰 {self.fmt(mise*2)} €",
        color=0xF1C40F
    )

    class PFCView(discord.ui.View):
        def __init__(self, cog, p1, p2, mise):
            super().__init__(timeout=120)
            self.cog, self.p1, self.p2, self.mise = cog, p1, p2, mise
            self.scores = {p1.id: 0, p2.id: 0}
            self.choices = {}

        async def play(self, i, choix):
            if i.user.id not in [self.p1.id, self.p2.id]:
                return

            if i.user.id in self.choices:
                return await i.response.send_message("❌ Déjà joué.", ephemeral=True)

            self.choices[i.user.id] = choix
            await i.response.send_message("✅ Choix enregistré", ephemeral=True)

            if len(self.choices) == 2:
                c1 = self.choices[self.p1.id]
                c2 = self.choices[self.p2.id]

                win_map = {"pierre": "ciseaux", "feuille": "pierre", "ciseaux": "feuille"}

                if c1 != c2:
                    winner = self.p1 if win_map[c1] == c2 else self.p2
                    self.scores[winner.id] += 1

                self.choices = {}

                if max(self.scores.values()) == 2:
                    gagnant = max(self.scores, key=self.scores.get)
                    gagnant_user = self.p1 if gagnant == self.p1.id else self.p2

                    gain = self.mise * 2
                    self.cog.update_money(gagnant_user.id, gain)

                    self.clear_items()

                    return await i.edit_original_response(
                        embed=discord.Embed(
                            title="🏆 VICTOIRE",
                            description=f"{gagnant_user.mention} gagne {self.cog.fmt(gain)} €"
                        ),
                        view=None
                    )

        @discord.ui.button(label="Pierre")
        async def pierre(self, i, b): await self.play(i, "pierre")

        @discord.ui.button(label="Feuille")
        async def feuille(self, i, b): await self.play(i, "feuille")

        @discord.ui.button(label="Ciseaux")
        async def ciseaux(self, i, b): await self.play(i, "ciseaux")

    # paiement
    self.update_money(interaction.user.id, -mise)
    self.update_money(adversaire.id, -mise)

    await interaction.response.send_message(embed=embed, view=PFCView(self, interaction.user, adversaire, mise))

# =========================
# 🪙 PILE OU FACE COMPLET
# =========================

@group.command(name="pileouface", description="🪙 Double ta mise")
async def pileouface(self, interaction: discord.Interaction, pari: int):
    solde = self.get_user(interaction.user.id)

    err = self.check_mise(pari, 10, 10000, solde)
    if err:
        return await interaction.response.send_message(err, ephemeral=True)

    self.update_money(interaction.user.id, -pari)

    class PFView(discord.ui.View):
        def __init__(self, cog, user, pari):
            super().__init__(timeout=30)
            self.cog, self.user, self.pari = cog, user, pari
            self.done = False

        async def play(self, i, choix):
            if self.done:
                return

            if i.user.id != self.user.id:
                return

            self.done = True
            self.clear_items()

            res = random.choice(["pile", "face"])
            win = res == choix

            embed = discord.Embed(title="🪙 Résultat")

            if win:
                gain = self.pari * 2
                self.cog.update_money(self.user.id, gain)
                embed.description = f"✅ {res.upper()} ! +{self.cog.fmt(gain)} €"
            else:
                embed.description = f"💀 {res.upper()} ! Perdu."

            await i.response.edit_message(embed=embed, view=None)

        @discord.ui.button(label="PILE")
        async def pile(self, i, b): await self.play(i, "pile")

        @discord.ui.button(label="FACE")
        async def face(self, i, b): await self.play(i, "face")

    await interaction.response.send_message(
        embed=discord.Embed(title="🪙 Pile ou Face"),
        view=PFView(self, interaction.user, pari)
    )

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

@group.command(name="risque", description="🏔️ Survis à 5 étapes mortelles pour gagner 500 € ! (Mise fixe : 65 €)")
    async def risque(self, interaction: discord.Interaction, mise: int):
        # --- CONDITION DE MISE STRICTE ---
        if mise != 65:
            return await interaction.response.send_message("⚠️ **Refusé** : Le jeu **RISQUE** nécessite une mise précise de **65 €**.", ephemeral=True)

        solde = self.get_user(interaction.user.id)
        if solde < mise:
            return await interaction.response.send_message("❌ Tu n'as pas les 65 € nécessaires.", ephemeral=True)

        # Prélèvement immédiat
        self.update_money(interaction.user.id, -65)

        view = RisqueView(self, interaction.user)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

class RisqueView(discord.ui.View):
    def __init__(self, cog, user):
        super().__init__(timeout=120)
        self.cog = cog
        self.user = user
        self.niveau = 1
        # Config : bombes, gain de l'étape, nombre de cases
        self.config = {
            1: {"b": 1, "g": 10, "c": 5},
            2: {"b": 2, "g": 15, "c": 5},
            3: {"b": 3, "g": 70, "c": 5},
            4: {"b": 4, "g": 200, "c": 5},
            5: {"b": 1, "g": 500, "c": 2}
        }
        self.cagnotte = 0

    def make_embed(self):
        conf = self.config[self.niveau]
        progression = "▰" * self.niveau + "▱" * (5 - self.niveau)
        
        embed = discord.Embed(
            title="☢️ MODE RISQUE",
            description=(
                f"**Niveau {self.niveau}/5**\n`{progression}`\n\n"
                f"Il y a **{conf['b']} bombe(s)** cachée(s) parmi **{conf['c']} cases**.\n"
                f"Si tu réussis, tu gagnes **+{conf['g']} €**."
            ),
            color=0xF39C12
        )
        embed.add_field(name="💰 Cagnotte actuelle", value=f"**{self.cog.fmt(self.cagnotte)} €**")
        embed.set_footer(text="Attention : Un seul faux pas et tout est perdu !")
        return embed

    async def check_step(self, interaction, choice):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Ce n'est pas ta partie.", ephemeral=True)

        conf = self.config[self.niveau]
        # On place les bombes
        bombes = random.sample(range(1, conf['c'] + 1), conf['b'])

        if choice in bombes:
            # PERDU
            embed = discord.Embed(
                title="💥 BOUM ! TERMINÉ.",
                description=f"Tu as touché une mine au niveau {self.niveau}.\nTu perds tes **65 €** et ta progression.",
                color=0xC0392B
            )
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            # GAGNÉ
            self.cagnotte += conf['g']
            
            if self.niveau < 5:
                self.niveau += 1
                # On met à jour les boutons pour le prochain niveau
                new_view = RisqueButtons(self)
                await interaction.response.edit_message(embed=self.make_embed(), view=new_view)
            else:
                # VICTOIRE FINALE
                self.cog.update_money(self.user.id, self.cagnotte)
                embed = discord.Embed(
                    title="🏆 L'ULTIME SURVIVANT !",
                    description=f"Tu as bravé tous les dangers !\n\nTotal remporté : **{self.cog.fmt(self.cagnotte)} €**",
                    color=0x27AE60
                )
                await interaction.response.edit_message(embed=embed, view=None)

class RisqueButtons(discord.ui.View):
    def __init__(self, parent):
        super().__init__(timeout=120)
        self.parent = parent
        nb_cases = self.parent.config[self.parent.niveau]["c"]
        
        for i in range(1, nb_cases + 1):
            btn = discord.ui.Button(
                label=f"Case {i}", 
                style=discord.ButtonStyle.primary if nb_cases > 2 else discord.ButtonStyle.danger,
                custom_id=str(i)
            )
            btn.callback = self.get_callback(i)
            self.add_item(btn)

    def get_callback(self, i):
        async def callback(interaction):
            await self.parent.check_step(interaction, i)
        return callback

@group.command(name="uno", description="🃏 UNO Pro 2v2 : Le premier à vider sa main fait gagner son équipe !")
    async def uno(self, interaction: discord.Interaction, coequipier: discord.Member, adversaire1: discord.Member, adversaire2: discord.Member, mise: int):
        joueurs = [interaction.user, coequipier, adversaire1, adversaire2]
        
        if len(set(joueurs)) < 4: return await interaction.response.send_message("❌ 4 joueurs réels requis.", ephemeral=True)
        for p in joueurs:
            if self.get_user(p.id) < mise:
                return await interaction.response.send_message(f"❌ {p.display_name} n'a pas les fonds ({mise} €).", ephemeral=True)

        # Débit immédiat (Casino Rule)
        for p in joueurs: self.update_money(p.id, -mise)

        view = UnoView(self, joueurs, mise)
        await interaction.response.send_message(
            content=f"🃏 **PARTIE DE UNO LANCÉE** | Enjeu : **{self.fmt(mise*4)} €**\n🔵 **Équipe A** : {joueurs[0].mention} & {joueurs[1].mention}\n🔴 **Équipe B** : {joueurs[2].mention} & {joueurs[3].mention}",
            embed=view.make_embed(),
            view=view
        )

class UnoView(discord.ui.View):
    def __init__(self, cog, joueurs, mise):
        super().__init__(timeout=600)
        self.cog, self.joueurs, self.mise = cog, joueurs, mise
        self.couleurs = ["🟥", "🟦", "🟩", "🟨"]
        self.valeurs = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "+2", "🚫", "🔄"]
        
        # Distribution (7 cartes comme en vrai)
        self.mains = {p.id: [f"{random.choice(self.couleurs)}{random.choice(self.valeurs)}" for _ in range(7)] for p in joueurs}
        # Ajout de 2 cartes Joker par joueur
        for p in joueurs: 
            if random.random() > 0.7: self.mains[p.id].append("🌈 Joker")
            if random.random() > 0.9: self.mains[p.id].append("🔥 +4")
            
        self.defausse = f"{random.choice(self.couleurs)}{random.choice(self.valeurs[:10])}"
        self.tour = 0
        self.direction = 1 # Pour le 🔄
        self.couleur_demandee = None # Pour le Joker/+4

    def make_embed(self):
        p_actuel = self.joueurs[self.tour]
        couleur_txt = self.couleur_demandee if self.couleur_demandee else self.defausse[0]
        
        embed = discord.Embed(title="🃏 TABLE DE UNO", description=f"Dernière carte : **{self.defausse}**\nCouleur active : **{couleur_txt}**", color=0x2b2d31)
        
        # Affichage des scores d'équipe
        score_a = len(self.mains[self.joueurs[0].id]) + len(self.mains[self.joueurs[1].id])
        score_b = len(self.mains[self.joueurs[2].id]) + len(self.mains[self.joueurs[3].id])
        
        embed.add_field(name="📊 Cartes restantes", value=f"🔵 Équipe A : `{score_a}`\n🔴 Équipe B : `{score_b}`", inline=False)
        embed.add_field(name="📍 C'est à toi", value=f"{p_actuel.mention}", inline=True)
        
        status = "\n".join([f"{'➡️' if i == self.tour else '👤'} {p.display_name} : {len(self.mains[p.id])} 🎴" for i, p in enumerate(self.joueurs)])
        embed.add_field(name="Joueurs", value=status, inline=True)
        
        return embed

    async def piocher(self, interaction):
        p_id = interaction.user.id
        self.mains[p_id].append(f"{random.choice(self.couleurs)}{random.choice(self.valeurs)}")
        self.tour = (self.tour + self.direction) % 4
        await interaction.response.edit_message(embed=self.make_embed(), view=UnoControl(self))

    async def jouer_carte(self, interaction, card_idx, nouvelle_couleur=None):
        p_id = interaction.user.id
        carte = self.mains[p_id].pop(card_idx)
        self.defausse = carte
        self.couleur_demandee = nouvelle_couleur # Utilisé si Joker

        # --- EFFETS ---
        skip = False
        pick = 0
        if "🚫" in carte: skip = True
        elif "🔄" in carte: self.direction *= -1
        elif "+2" in carte: pick = 2
        elif "+4" in carte: pick = 4; self.couleur_demandee = nouvelle_couleur
        elif "Joker" in carte: self.couleur_demandee = nouvelle_couleur
        else: self.couleur_demandee = None

        # --- VICTOIRE ---
        if len(self.mains[p_id]) == 0:
            gagnants = self.joueurs[0:2] if p_id in [self.joueurs[0].id, self.joueurs[1].id] else self.joueurs[2:4]
            total_gain = self.mise * 2
            for g in gagnants: self.cog.update_money(g.id, total_gain)
            
            emb = discord.Embed(title="🏆 UNO ! VICTOIRE FINALE !", description=f"L'équipe de **{interaction.user.mention}** gagne la partie !\n💰 Chaque membre reçoit : **{self.cog.fmt(total_gain)} €**", color=0xF1C40F)
            return await interaction.edit_original_response(embed=emb, view=None)

        # --- PROCHAIN TOUR ---
        self.tour = (self.tour + (self.direction * (2 if skip else 1))) % 4
        if pick > 0:
            victime = self.joueurs[self.tour].id
            for _ in range(pick): self.mains[victime].append(f"{random.choice(self.couleurs)}{random.choice(self.valeurs)}")
            self.tour = (self.tour + self.direction) % 4 # On saute le tour de celui qui a pioché

        await interaction.response.edit_message(embed=self.make_embed(), view=UnoControl(self))

class UnoControl(discord.ui.View):
    def __init__(self, parent):
        super().__init__(timeout=300)
        self.parent = parent
        self.setup_options()

    def setup_options(self):
        p_id = self.parent.joueurs[self.parent.tour].id
        main = self.parent.mains[p_id]
        couleur_active = self.parent.couleur_demandee if self.parent.couleur_demandee else self.parent.defausse[0]
        valeur_active = self.parent.defausse[1:]

        options = []
        for i, c in enumerate(main):
            # Logique de pose de carte
            jouable = ("Joker" in c or "+4" in c or c[0] == couleur_active or c[1:] == valeur_active)
            if jouable:
                options.append(discord.SelectOption(label=f"Jouer {c}", value=str(i)))

        if not options:
            options.append(discord.SelectOption(label="Aucune carte jouable (Piochez)", value="draw"))

        select = discord.ui.Select(placeholder="🎴 Choisis ta carte...", options=options[:25])
        
        async def callback(i):
            if i.user.id != p_id: return await i.response.send_message("❌ Patiente, ce n'est pas ton tour !", ephemeral=True)
            val = select.values[0]
            if val == "draw": return await self.parent.piocher(i)
            
            carte_choisie = main[int(val)]
            if "Joker" in carte_choisie or "+4" in carte_choisie:
                # Si c'est un joker, on demande la couleur avec un nouveau menu
                return await i.response.edit_message(content="🎨 **Choisis la nouvelle couleur :**", view=ColorPicker(self.parent, int(val)))
            
            await self.parent.jouer_carte(i, int(val))

        select.callback = callback
        self.add_item(select)

    @discord.ui.button(label="Voir ma main", emoji="👁️", style=discord.ButtonStyle.gray)
    async def show(self, i, b):
        m = self.parent.mains.get(i.user.id, [])
        await i.response.send_message(f"🃏 Ta main : **{' | '.join(m)}**", ephemeral=True)

class ColorPicker(discord.ui.View):
    def __init__(self, parent, card_idx):
        super().__init__(timeout=60)
        self.parent, self.idx = parent, card_idx

    async def pick(self, i, color):
        await self.parent.jouer_carte(i, self.idx, color)

    @discord.ui.button(label="Rouge", emoji="🟥")
    async def r(self, i, b): await self.pick(i, "🟥")
    @discord.ui.button(label="Bleu", emoji="🟦")
    async def b(self, i, b): await self.pick(i, "🟦")
    @discord.ui.button(label="Vert", emoji="🟩")
    async def v(self, i, b): await self.pick(i, "🟩")
    @discord.ui.button(label="Jaune", emoji="🟨")
    async def j(self, i, b): await self.pick(i, "🟨")

# --- TRUCS DE FIN ---
async def setup(bot):
    await bot.add_cog(Jeux(bot))
