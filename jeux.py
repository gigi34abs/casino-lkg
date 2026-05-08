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

# =========================
# 🪙 PILE OU FACE
# =========================

    @jeux.command(name="pileouface", description="🪙 Double ou rien")
    async def pileouface(self, interaction: discord.Interaction, mise: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 10, 20000, solde)

        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        self.update_money(interaction.user.id, -mise)

        embed = discord.Embed(
            title="🪙 PILE OU FACE",
            description="Choisis ton camp 👇",
            color=0x3498DB
        )

        embed.add_field(name="💰 Mise", value=f"{self.fmt(mise)} €")
        embed.add_field(name="🎯 Gain possible", value=f"{self.fmt(mise*2)} €")

        class PFView(discord.ui.View):
            def __init__(self, cog, user):
                super().__init__(timeout=30)
                self.cog = cog
                self.user = user
                self.played = False

            async def play(self, i, choix):
                if self.played: return
                if i.user.id != self.user.id:
                    return await i.response.send_message("❌ Ce n'est pas ton jeu.", ephemeral=True)

                self.played = True
                self.clear_items()
                res = random.choice(["pile", "face"])
                embed = discord.Embed(title="🪙 RÉSULTAT")

                if res == choix:
                    gain = mise * 2
                    self.cog.update_money(self.user.id, gain)
                    embed.description = f"✅ **{res.upper()} !** Tu gagnes {self.cog.fmt(gain)} €"
                    embed.color = 0x2ECC71
                else:
                    embed.description = f"💀 **{res.upper()} !** Tu perds ta mise"
                    embed.color = 0xE74C3C

                await i.response.edit_message(embed=embed, view=None)

            @discord.ui.button(label="PILE", emoji="🪙", style=discord.ButtonStyle.primary)
            async def pile(self, i, b): await self.play(i, "pile")

            @discord.ui.button(label="FACE", emoji="🎯", style=discord.ButtonStyle.secondary)
            async def face(self, i, b): await self.play(i, "face")

        await interaction.response.send_message(embed=embed, view=PFView(self, interaction.user))


# =========================
# 🔢 MYSTÈRE
# =========================

    @jeux.command(name="mystere", description="🔢 Plus haut ou plus bas")
    async def mystere(self, interaction: discord.Interaction, mise: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 1, 5000, solde)

        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        self.update_money(interaction.user.id, -mise)

        bc = random.randint(1, 14)
        uc = random.randint(1, 14)
        while uc == bc: uc = random.randint(1, 14)

        embed = discord.Embed(
            title="🔢 JEU MYSTÈRE",
            description=f"La banque a tiré : **{bc}**\n\nTon nombre est caché...\nPlus haut ou plus bas ?",
            color=0x9B59B6
        )
        embed.add_field(name="💰 Mise", value=f"{self.fmt(mise)} €")
        embed.add_field(name="🎯 Gain", value=f"{self.fmt(mise*2)} €")

        class MystereView(discord.ui.View):
            def __init__(self, cog, user):
                super().__init__(timeout=30)
                self.cog = cog
                self.user = user
                self.played = False

            async def play(self, i, choix):
                if self.played: return
                if i.user.id != self.user.id:
                    return await i.response.send_message("❌ Pas ton jeu.", ephemeral=True)

                self.played = True
                self.clear_items()
                win = (choix == "haut" and uc > bc) or (choix == "bas" and uc < bc)
                embed = discord.Embed(title="🔢 RÉSULTAT")

                if win:
                    gain = mise * 2
                    self.cog.update_money(self.user.id, gain)
                    embed.description = f"✅ {uc} vs {bc}\nTu gagnes {gain} €"
                    embed.color = 0x2ECC71
                else:
                    embed.description = f"💀 {uc} vs {bc}\nPerdu"
                    embed.color = 0xE74C3C

                await i.response.edit_message(embed=embed, view=None)

            @discord.ui.button(label="PLUS HAUT", emoji="⬆️", style=discord.ButtonStyle.success)
            async def haut(self, i, b): await self.play(i, "haut")

            @discord.ui.button(label="PLUS BAS", emoji="⬇️", style=discord.ButtonStyle.danger)
            async def bas(self, i, b): await self.play(i, "bas")

        await interaction.response.send_message(embed=embed, view=MystereView(self, interaction.user))

# =========================
# 🚪 PORTES
# =========================

    @jeux.command(name="portes", description="🚪 Trouve la bonne porte")
    async def portes(self, interaction: discord.Interaction, mise: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 10, 5000, solde)

        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        self.update_money(interaction.user.id, -mise)
        bonne_porte = random.randint(1, 3)

        embed = discord.Embed(
            title="🚪 CHOISIS UNE PORTE",
            description="Derrière une porte se cache un trésor... les autres = 💀",
            color=0xE67E22
        )
        embed.add_field(name="💰 Mise", value=f"{self.fmt(mise)} €")
        embed.add_field(name="🎯 Gain", value=f"{self.fmt(mise*3)} €")

        class PortesView(discord.ui.View):
            def __init__(self, cog, user):
                super().__init__(timeout=30)
                self.cog = cog
                self.user = user
                self.done = False

            async def choisir(self, i, choix):
                if self.done: return
                if i.user.id != self.user.id:
                    return await i.response.send_message("❌ Pas ton jeu.", ephemeral=True)

                self.done = True
                self.clear_items()
                embed = discord.Embed(title="🚪 RÉSULTAT")

                if choix == bonne_porte:
                    gain = mise * 3
                    self.cog.update_money(self.user.id, gain)
                    embed.description = f"🎉 Bonne porte ! (+{gain} €)"
                    embed.color = 0x2ECC71
                else:
                    embed.description = f"💀 Mauvaise porte...\nLa bonne était : {bonne_porte}"
                    embed.color = 0xE74C3C

                await i.response.edit_message(embed=embed, view=None)

            @discord.ui.button(label="Porte 1", emoji="🚪")
            async def p1(self, i, b): await self.choisir(i, 1)

            @discord.ui.button(label="Porte 2", emoji="🚪")
            async def p2(self, i, b): await self.choisir(i, 2)

            @discord.ui.button(label="Porte 3", emoji="🚪")
            async def p3(self, i, b): await self.choisir(i, 3)

        await interaction.response.send_message(embed=embed, view=PortesView(self, interaction.user))


# =========================
# ☢️ RISQUE
# =========================

    @jeux.command(name="risque", description="☢️ Monte les niveaux sans exploser")
    async def risque(self, interaction: discord.Interaction, mise: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 50, 5000, solde)

        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        self.update_money(interaction.user.id, -mise)

        embed = discord.Embed(
            title="☢️ JEU DU RISQUE",
            description="Clique pour monter les niveaux...\nMais attention à la bombe 💣",
            color=0xC0392B
        )
        embed.add_field(name="💰 Mise", value=f"{self.fmt(mise)} €")

        class RiskView(discord.ui.View):
            def __init__(self, cog, user):
                super().__init__(timeout=60)
                self.cog = cog
                self.user = user
                self.level = 1
                self.gain = mise

            async def jouer(self, i):
                if i.user.id != self.user.id:
                    return await i.response.send_message("❌ Pas ton jeu.", ephemeral=True)

                if random.randint(1, 4) == 1:
                    self.clear_items()
                    return await i.response.edit_message(
                        embed=discord.Embed(
                            title="💥 BOOM !",
                            description="Tu as tout perdu...",
                            color=0xE74C3C
                        ), view=None
                    )

                self.level += 1
                self.gain = int(self.gain * 1.5)
                embed = discord.Embed(
                    title="☢️ RISQUE",
                    description=f"✅ Niveau {self.level}\n💰 Gain actuel : {self.gain} €",
                    color=0x2ECC71
                )
                await i.response.edit_message(embed=embed, view=self)

            @discord.ui.button(label="🎲 Continuer", style=discord.ButtonStyle.primary)
            async def continuer(self, i, b): await self.jouer(i)

            @discord.ui.button(label="💰 Encaisser", style=discord.ButtonStyle.success)
            async def cashout(self, i, b):
                if i.user.id != self.user.id: return
                self.cog.update_money(self.user.id, self.gain)
                self.clear_items()
                await i.response.edit_message(
                    embed=discord.Embed(
                        title="💰 CASHOUT",
                        description=f"Tu repars avec {self.gain} €",
                        color=0xF1C40F
                    ), view=None
                )

        await interaction.response.send_message(embed=embed, view=RiskView(self, interaction.user))

# =========================
# 🏇 COURSE (ANIMÉE)
# =========================

    @jeux.command(name="course", description="🏇 Course entre joueurs")
    async def course(self, interaction: discord.Interaction, mise: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 50, 5000, solde)

        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        joueurs = [interaction.user]

        class CourseView(discord.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=30)
                self.cog = cog

            @discord.ui.button(label="➕ Rejoindre", style=discord.ButtonStyle.success)
            async def join(self, i, b):
                if i.user in joueurs:
                    return await i.response.send_message("❌ Déjà dans la course", ephemeral=True)
                if self.cog.get_user(i.user.id) < mise:
                    return await i.response.send_message("❌ Pas assez d'argent", ephemeral=True)
                joueurs.append(i.user)
                await i.response.send_message("✅ Tu rejoins la course !", ephemeral=True)

            @discord.ui.button(label="🚀 Lancer", style=discord.ButtonStyle.primary)
            async def start(self, i, b):
                if i.user != interaction.user: return
                if len(joueurs) < 1: return

                for p in joueurs:
                    self.cog.update_money(p.id, -mise)

                positions = {p: 0 for p in joueurs}
                for tour in range(8):
                    msg = "🏇 **COURSE EN COURS**\n\n"
                    for p in positions:
                        positions[p] += random.randint(1, 3)
                        bar = "🐎" * positions[p]
                        msg += f"{p.display_name} : {bar}\n"
                    await i.response.edit_message(content=msg, view=None) if tour == 0 else await interaction.edit_original_response(content=msg)
                    await asyncio.sleep(1)

                gagnant = max(positions, key=positions.get)
                gain = mise * len(joueurs)
                self.cog.update_money(gagnant.id, gain)
                await interaction.edit_original_response(content=f"🏆 {gagnant.mention} gagne la course !\n💰 Gain : {gain} €")

        embed = discord.Embed(
            title="🏇 COURSE",
            description="Clique pour rejoindre puis lance !",
            color=0x1ABC9C
        )
        embed.add_field(name="💰 Mise", value=f"{self.fmt(mise)} €")
        await interaction.response.send_message(embed=embed, view=CourseView(self))


# =========================
# ⚔️ PFC (DUEL BO3)
# =========================

    @jeux.command(name="pfc", description="⚔️ Pierre Feuille Ciseaux (BO3)")
    async def pfc(self, interaction: discord.Interaction, mise: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 10, 5000, solde)

        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        joueurs = [interaction.user]

        class PFCJoin(discord.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=30)
                self.cog = cog

            @discord.ui.button(label="⚔️ Rejoindre", style=discord.ButtonStyle.success)
            async def join(self, i, b):
                if i.user == interaction.user: return
                if len(joueurs) >= 2:
                    return await i.response.send_message("❌ Déjà 2 joueurs", ephemeral=True)
                if self.cog.get_user(i.user.id) < mise:
                    return await i.response.send_message("❌ Pas assez d'argent", ephemeral=True)

                joueurs.append(i.user)
                await i.response.send_message("✅ Duel accepté", ephemeral=True)
                for p in joueurs: self.cog.update_money(p.id, -mise)
                await interaction.edit_original_response(content=f"⚔️ Duel entre {joueurs[0].mention} et {joueurs[1].mention}", view=PFCGame(self.cog))

        class PFCGame(discord.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=60)
                self.cog = cog
                self.choices = {}
                self.score = {joueurs[0]: 0, joueurs[1]: 0}

            async def check_round(self, i):
                if len(self.choices) < 2: return
                p1, p2 = joueurs
                c1, c2 = self.choices[p1], self.choices[p2]
                result = ""

                if c1 == c2: result = "🤝 Égalité"
                elif (c1 == "pierre" and c2 == "ciseaux") or (c1 == "feuille" and c2 == "pierre") or (c1 == "ciseaux" and c2 == "feuille"):
                    self.score[p1] += 1
                    result = f"🏆 {p1.display_name} gagne le round"
                else:
                    self.score[p2] += 1
                    result = f"🏆 {p2.display_name} gagne le round"

                txt = f"{result}\nScore : {self.score[p1]} - {self.score[p2]}"
                self.choices = {}

                if self.score[p1] == 2 or self.score[p2] == 2:
                    gagnant = p1 if self.score[p1] == 2 else p2
                    gain = mise * 2
                    self.cog.update_money(gagnant.id, gain)
                    self.clear_items()
                    return await i.response.edit_message(content=f"🏆 {gagnant.mention} gagne le duel ! (+{gain}€)", view=None)
                await i.response.edit_message(content=txt, view=self)

            async def play(self, i, choix):
                if i.user not in joueurs: return
                self.choices[i.user] = choix
                await self.check_round(i)

            @discord.ui.button(label="🪨")
            async def pierre(self, i, b): await self.play(i, "pierre")
            @discord.ui.button(label="📄")
            async def feuille(self, i, b): await self.play(i, "feuille")
            @discord.ui.button(label="✂️")
            async def ciseaux(self, i, b): await self.play(i, "ciseaux")

        embed = discord.Embed(title="⚔️ PFC", description="Un joueur rejoint pour commencer", color=0xE91E63)
        embed.add_field(name="💰 Mise", value=f"{self.fmt(mise)} €")
        await interaction.response.send_message(embed=embed, view=PFCJoin(self))

 # =========================
# 🃏 JEU DU UNO
# =========================

    @jeux.command(name="uno", description="🃏 Jeu UNO (équipe)")
    async def uno(self, interaction: discord.Interaction):
        joueurs = []
        equipes = {"bleu": [], "orange": []}

        class JoinView(discord.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=60)
                self.cog = cog

            @discord.ui.button(label="🔵 Équipe Bleue", style=discord.ButtonStyle.primary)
            async def bleu(self, i, b):
                if i.user in joueurs: 
                    return await i.response.send_message("❌ Tu es déjà dans une équipe !", ephemeral=True)
                joueurs.append(i.user)
                equipes["bleu"].append(i.user)
                await i.response.send_message("🔵 Tu as rejoint l'équipe **Bleue** !", ephemeral=True)

            @discord.ui.button(label="🟠 Équipe Orange", style=discord.ButtonStyle.secondary)
            async def orange(self, i, b):
                if i.user in joueurs: 
                    return await i.response.send_message("❌ Tu es déjà dans une équipe !", ephemeral=True)
                joueurs.append(i.user)
                equipes["orange"].append(i.user)
                await i.response.send_message("🟠 Tu as rejoint l'équipe **Orange** !", ephemeral=True)

            @discord.ui.button(label="🚀 Lancer la partie", style=discord.ButtonStyle.success)
            async def start(self, i, b):
                # Seul celui qui a lancé la commande peut démarrer
                if i.user != interaction.user: 
                    return await i.response.send_message("❌ Seul l'organisateur peut lancer !", ephemeral=True)
                
                if len(joueurs) < 2: 
                    return await i.response.send_message("❌ Il faut au moins 2 joueurs pour commencer !", ephemeral=True)

                # On désactive les boutons
                self.clear_items()
                await i.response.edit_message(content="🃏 **La partie commence... Préparez vos cartes !**", view=None)
                
                score_bleu = 0
                score_orange = 0

                # Simulation des tours (7 manches)
                for tour in range(1, 8):
                    await asyncio.sleep(1.5)
                    gagnant_tour = random.choice(["bleu", "orange"])
                    
                    if gagnant_tour == "bleu":
                        score_bleu += 1
                    else:
                        score_orange += 1

                    txt = (
                        f"🃏 **DÉROULEMENT DU UNO - TOUR {tour}/7**\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🔵 Équipe Bleue : `{score_bleu}`\n"
                        f"🟠 Équipe Orange : `{score_orange}`\n\n"
                        f"🎯 Manche remportée par : **{gagnant_tour.upper()}** !"
                    )
                    await interaction.edit_original_response(content=txt)

                # Détermination du vainqueur final
                gagnant_final = "bleu" if score_bleu > score_orange else "orange"
                couleur_emoji = "🔵" if gagnant_final == "bleu" else "🟠"

                # TON MESSAGE DE FIN PERSO
                txt_final = (
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "🏆 **UNO ! VICTOIRE FINALE !**\n\n"
                    f"🔥 L'équipe **{gagnant_final.upper()}** {couleur_emoji} écrase la partie !\n"
                    "💥 Dernière carte posée avec style, personne n'a pu contrer !\n\n"
                    "💰 **GG à tous les joueurs !**"
                )

                await interaction.edit_original_response(content=txt_final)

        # Message d'invitation initial
        embed = discord.Embed(
            title="🃏 SESSION DE UNO",
            description=(
                "Le jeu va commencer ! Choisissez votre camp ci-dessous.\n\n"
                "🔹 **Équipe Bleue** vs 🔸 **Équipe Orange**"
            ),
            color=0xF39C12 # Orange UNO
        )
        embed.set_footer(text="Organisé par " + interaction.user.display_name)
        
        await interaction.response.send_message(embed=embed, view=JoinView(self))

async def setup(bot):
    await bot.add_cog(Jeux(bot))
