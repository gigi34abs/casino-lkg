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

# =========================
# 🚪 PORTES COMPLET
# =========================

@group.command(name="portes", description="🚪 Trouve la bonne porte")
async def portes(self, interaction: discord.Interaction, pari: int):
    solde = self.get_user(interaction.user.id)

    err = self.check_mise(pari, 1, 10000, solde)
    if err:
        return await interaction.response.send_message(err, ephemeral=True)

    self.update_money(interaction.user.id, -pari)
    win = random.randint(1, 3)

    class PortesView(discord.ui.View):
        def __init__(self, cog, user):
            super().__init__(timeout=30)
            self.cog, self.user = cog, user

        async def choose(self, i, choix):
            if i.user.id != self.user.id:
                return

            self.clear_items()

            if choix == win:
                gain = pari * 3
                self.cog.update_money(self.user.id, gain)
                msg = f"💰 Gagné ! {gain} €"
            else:
                msg = "💀 Perdu"

            await i.response.edit_message(content=msg, view=None)

        @discord.ui.button(label="1")
        async def b1(self, i, b): await self.choose(i, 1)

        @discord.ui.button(label="2")
        async def b2(self, i, b): await self.choose(i, 2)

        @discord.ui.button(label="3")
        async def b3(self, i, b): await self.choose(i, 3)

    await interaction.response.send_message("Choisis une porte", view=PortesView(self, interaction.user))

# =========================
# ☢️ RISQUE COMPLET
# =========================

@group.command(name="risque", description="☢️ Jeu à étapes")
async def risque(self, interaction: discord.Interaction, mise: int):
    if mise != 65:
        return await interaction.response.send_message("❌ Mise fixe : 65 €", ephemeral=True)

    if self.get_user(interaction.user.id) < 65:
        return await interaction.response.send_message("❌ Pas assez d'argent", ephemeral=True)

    self.update_money(interaction.user.id, -65)

    class RiskView(discord.ui.View):
        def __init__(self, cog, user):
            super().__init__()
            self.cog, self.user = cog, user
            self.level = 1
            self.gain = 0

        async def play(self, i):
            if i.user.id != self.user.id:
                return

            bomb = random.randint(1, 3)

            if random.randint(1, 3) == bomb:
                self.clear_items()
                return await i.response.edit_message(content="💥 Perdu", view=None)

            self.gain += 50

            if self.level == 5:
                self.cog.update_money(self.user.id, self.gain)
                self.clear_items()
                return await i.response.edit_message(content=f"🏆 {self.gain} €", view=None)

            self.level += 1
            await i.response.edit_message(content=f"Niveau {self.level}", view=self)

        @discord.ui.button(label="Jouer")
        async def jouer(self, i, b): await self.play(i)

    await interaction.response.send_message("☢️ Risque", view=RiskView(self, interaction.user))

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

# =========================
# 🃏 UNO PRO MAX
# =========================

@group.command(name="uno", description="🃏 UNO équipes avancé")
async def uno(self, interaction: discord.Interaction, mise: int):

    if self.get_user(interaction.user.id) < mise:
        return await interaction.response.send_message("❌ Pas assez d'argent.", ephemeral=True)

    joueurs = []
    bleu = []
    orange = []

    class Lobby(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=90)
            self.cog = cog

        async def update(self, i):
            embed = discord.Embed(
                title="🃏 LOBBY UNO",
                description=(
                    f"🔵 BLEU ({len(bleu)}/2)\n" +
                    "\n".join([p.display_name for p in bleu]) + "\n\n"
                    f"🟠 ORANGE ({len(orange)}/2)\n" +
                    "\n".join([p.display_name for p in orange])
                )
            )
            await i.response.edit_message(embed=embed, view=self)

        @discord.ui.button(label="🔵 BLEU", style=discord.ButtonStyle.primary)
        async def b(self, i, _):
            if i.user in joueurs or len(bleu) >= 2:
                return await i.response.send_message("❌ Impossible", ephemeral=True)
            joueurs.append(i.user); bleu.append(i.user)
            await self.update(i)

        @discord.ui.button(label="🟠 ORANGE", style=discord.ButtonStyle.secondary)
        async def o(self, i, _):
            if i.user in joueurs or len(orange) >= 2:
                return await i.response.send_message("❌ Impossible", ephemeral=True)
            joueurs.append(i.user); orange.append(i.user)
            await self.update(i)

        @discord.ui.button(label="🚀 Lancer", style=discord.ButtonStyle.success)
        async def start(self, i, _):
            if i.user != interaction.user:
                return await i.response.send_message("❌ Host uniquement", ephemeral=True)

            if len(joueurs) != 4:
                return await i.response.send_message("❌ 4 joueurs requis", ephemeral=True)

            self.clear_items()

            for p in joueurs:
                self.cog.update_money(p.id, -mise)

            game = UnoGame(self.cog, joueurs, bleu, orange, mise)
            await i.response.edit_message(embed=game.embed(), view=game)

    class UnoGame(discord.ui.View):
        def __init__(self, cog, joueurs, bleu, orange, mise):
            super().__init__(timeout=900)
            self.cog = cog
            self.players = joueurs
            self.bleu = bleu
            self.orange = orange
            self.mise = mise
            self.turn = 0
            self.sens = 1

            couleurs = ["🟥","🟦","🟩","🟨"]
            valeurs = [str(i) for i in range(10)] + ["+2","⏭","🔄"]

            def rand_card():
                return random.choice(couleurs) + random.choice(valeurs)

            self.hands = {p.id: [rand_card() for _ in range(7)] for p in joueurs}
            self.discard = rand_card()

        def embed(self):
            p = self.players[self.turn]
            return discord.Embed(
                title="🃏 UNO PRO",
                description=(
                    f"Carte : {self.discard}\n\n"
                    f"Tour : {p.mention}\n\n"
                    f"🔵 Bleu : {sum(len(self.hands[j.id]) for j in self.bleu)} cartes\n"
                    f"🟠 Orange : {sum(len(self.hands[j.id]) for j in self.orange)} cartes"
                )
            )

        def next(self):
            self.turn = (self.turn + self.sens) % 4

        async def play_card(self, i):
            if i.user != self.players[self.turn]:
                return await i.response.send_message("❌ Pas ton tour", ephemeral=True)

            hand = self.hands[i.user.id]

            if not hand:
                return

            card = hand.pop(0)
            self.discard = card

            # effets
            if "+2" in card:
                self.next()
                self.hands[self.players[self.turn].id] += ["🟥0","🟦0"]

            elif "⏭" in card:
                self.next()

            elif "🔄" in card:
                self.sens *= -1

            # victoire
            if len(hand) == 0:
                winners = self.bleu if i.user in self.bleu else self.orange
                gain = self.mise * 2

                for w in winners:
                    self.cog.update_money(w.id, gain)

                self.clear_items()

                return await i.response.edit_message(
                    embed=discord.Embed(
                        title="🏆 UNO ! VICTOIRE FINALE !",
                        description=(
                            f"L'équipe {'🔵 Bleue' if i.user in self.bleu else '🟠 Orange'} écrase la partie !\n\n"
                            f"🔥 {i.user.mention} pose sa dernière carte comme un boss.\n"
                            f"💥 La table est en PLS.\n\n"
                            f"💰 Gain : **{self.cog.fmt(gain)} €** chacun"
                        ),
                        color=0xF1C40F
                    ),
                    view=None
                )

            self.next()
            await i.response.edit_message(embed=self.embed(), view=self)

        @discord.ui.button(label="🃏 Jouer")
        async def jouer(self, i, _):
            await self.play_card(i)

        @discord.ui.button(label="👁 Voir main")
        async def main(self, i, _):
            await i.response.send_message(
                " | ".join(self.hands.get(i.user.id, [])),
                ephemeral=True
            )

    await interaction.response.send_message(
        embed=discord.Embed(title="🃏 UNO", description="Choisis ton équipe 🔵 ou 🟠"),
        view=Lobby(self)
            )

# --- TRUCS DE FIN ---
async def setup(bot):
    await bot.add_cog(Jeux(bot))
