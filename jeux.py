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

    # ==================== MYSTÈRE AMÉLIORÉ ====================
    @group.command(name="mystere", description=" Devine si ton nombre sera plus haut ou plus bas (1-14)")
    async def mystere(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(pari, 1, 2500, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        bc = random.randint(1, 14)
        uc = random.randint(1, 14)

        embed = discord.Embed(title="🔢 JEU DU MYSTÈRE", description=f"Le nombre de la banque est : **{bc}**\n\nTon nombre est caché. Sera-t-il plus **Haut** ou plus **Bas** ?", color=0x3498DB)
        embed.add_field(name="💰 Mise engagée", value=f"`{self.fmt(pari)} €`", inline=True)
        embed.add_field(name="📈 Gain potentiel", value=f"`{self.fmt(round(pari*1.5))} €`", inline=True)

        class MystereView(discord.ui.View):
            def __init__(self, cog, bc, uc, pari):
                super().__init__(timeout=30)
                self.cog = cog
                self.bc = bc
                self.uc = uc
                self.pari = pari

            async def process_choice(self, i: discord.Interaction, choice: str):
                if i.user.id != interaction.user.id: return await i.response.send_message("❌ Pas ton tour !", ephemeral=True)
                res_embed = discord.Embed(description=f"Banque : **{self.bc}**\nToi : **{self.uc}**", color=0x3498DB)
                
                if self.uc == self.bc:
                    res_embed.title = "🤝 ÉGALITÉ"; res_embed.color = 0x95A5A6
                elif (choice == "h" and self.uc > self.bc) or (choice == "b" and self.uc < self.bc):
                    gain = round(self.pari * 1.5)
                    self.cog.update_money(i.user.id, gain)
                    res_embed.title = "✅ VICTOIRE !"; res_embed.color = 0x2ECC71
                    res_embed.description += f"\n\nBravo ! Tu remportes **{self.cog.fmt(gain)} €**."
                else:
                    perte = self.pari * 2
                    self.cog.update_money(i.user.id, -perte)
                    res_embed.title = "💀 CRASH"; res_embed.color = 0xE74C3C
                    res_embed.description += f"\n\nMauvais pronostic ! Tu perds **{self.cog.fmt(perte)} €**."
                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="PLUS HAUT", emoji="⏫", style=discord.ButtonStyle.success)
            async def plus_haut(self, i, b): await self.process_choice(i, "h")
            @discord.ui.button(label="PLUS BAS", emoji="⏬", style=discord.ButtonStyle.danger)
            async def plus_bas(self, i, b): await self.process_choice(i, "b")

        await interaction.response.send_message(embed=embed, view=MystereView(self, bc, uc, pari))

# ==================== PORTES ====================
    @group.command(name="portes", description="🚪 Tente de trouver le trésor derrière l'une des 3 portes")
    async def portes(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(pari, 1, 10000, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        win_door = random.randint(1, 3)
        embed = discord.Embed(title="🚪 LE JEU DES PORTES", description="Choisis une porte !", color=0x9B59B6)
        embed.add_field(name="💰 Mise", value=f"`{self.fmt(pari)} €`")
        embed.add_field(name="🏆 Jackpot (x3)", value=f"`{self.fmt(pari*3)} €`")

        class PortesView(discord.ui.View):
            def __init__(self, cog, win_door, pari):
                super().__init__(timeout=30)
                self.cog = cog
                self.win_door = win_door
                self.pari = pari

            async def play(self, i: discord.Interaction, choice: int):
                if i.user.id != interaction.user.id: return await i.response.send_message("❌ Pas ton jeu !", ephemeral=True)
                result_text = "".join([f"Porte {n} : {'💰 **TRÉSOR**' if n == self.win_door else '💨 **VIDE**'}{' 👈' if choice == n else ''}\n" for n in range(1, 4)])
                res_embed = discord.Embed(title="🚪 RÉVÉLATION", description=result_text)

                if choice == self.win_door:
                    gain = self.pari * 3
                    self.cog.update_money(i.user.id, gain)
                    res_embed.title = "✨ VICTOIRE !"; res_embed.color = 0xF1C40F
                    res_embed.add_field(name="Résultat", value=f"Gain : **+{self.cog.fmt(gain)} €**")
                else:
                    perte = round(self.pari * 0.75)
                    self.cog.update_money(i.user.id, -perte)
                    res_embed.title = "💨 VIDE..."; res_embed.color = 0xE74C3C
                    res_embed.add_field(name="Résultat", value=f"Perte : **-{self.cog.fmt(perte)} €**")
                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="1", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b1(self, i, b): await self.play(i, 1)
            @discord.ui.button(label="2", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b2(self, i, b): await self.play(i, 2)
            @discord.ui.button(label="3", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b3(self, i, b): await self.play(i, 3)

        await interaction.response.send_message(embed=embed, view=PortesView(self, win_door, pari))

    # ==================== COURSE HIPPIQUE (2-6 JOUEURS) ====================
    @group.command(name="course", description="🏇 Course multijoueur (2-6 pers) : Le gagnant rafle toute la mise !")
    async def course(self, interaction: discord.Interaction, mise: int):
        solde_host = self.get_user(interaction.user.id)
        if mise < 50: return await interaction.response.send_message("❌ La mise minimale est de 50 €.", ephemeral=True)
        if solde_host < mise: return await interaction.response.send_message("❌ Tu n'as pas assez d'argent.", ephemeral=True)

        embed = discord.Embed(
            title="🏇 GRANDE COURSE HIPPIQUE",
            description=f"**{interaction.user.display_name}** organise une course !\n💰 Mise par personne : **{self.fmt(mise)} €**\n\nCliquez sur le bouton pour participer (Maximum 6).",
            color=0x27ae60
        )

        class CourseView(discord.ui.View):
            def __init__(self, cog, host, mise):
                super().__init__(timeout=60)
                self.cog = cog
                self.participants = [host]
                self.mise = mise
                self.started = False

            @discord.ui.button(label="Participer", emoji="🏇", style=discord.ButtonStyle.green)
            async def join(self, i: discord.Interaction, b: discord.ui.Button):
                if self.started: return await i.response.send_message("❌ Trop tard, la course a commencé !", ephemeral=True)
                if i.user.id in [p.id for p in self.participants]: return await i.response.send_message("❌ Tu es déjà inscrit !", ephemeral=True)
                if len(self.participants) >= 6: return await i.response.send_message("❌ La course est complète (6/6) !", ephemeral=True)
                
                s = self.cog.get_user(i.user.id)
                if s < self.mise: return await i.response.send_message("❌ Pas assez d'argent !", ephemeral=True)

                self.participants.append(i.user)
                n = len(self.participants)
                emb = i.message.embeds[0]
                emb.description = f"**Organisateur :** {self.participants[0].display_name}\n💰 Mise : **{self.cog.fmt(self.mise)} €**\n\n**Inscrits ({n}/6) :**\n" + "\n".join([f"• {p.display_name}" for p in self.participants])
                await i.response.edit_message(embed=emb, view=self)

            @discord.ui.button(label="Lancer la course !", emoji="🚩", style=discord.ButtonStyle.blurple)
            async def start(self, i: discord.Interaction, b: discord.ui.Button):
                if i.user.id != self.participants[0].id: return await i.response.send_message("❌ Seul l'organisateur peut lancer.", ephemeral=True)
                if len(self.participants) < 2: return await i.response.send_message("❌ Il faut au moins 2 joueurs !", ephemeral=True)
                
                self.started = True
                self.clear_items()
                await i.response.edit_message(content="🚦 **PRÊTS ? PARTEZ !**", view=self)

                # Prélèvement des mises
                for p in self.participants:
                    self.cog.update_money(p.id, -self.mise)

                # Animation rapide
                pistes = {p.display_name: 0 for p in self.participants}
                for _ in range(3):
                    await asyncio.sleep(1.5)
                    for p in pistes: pistes[p] += random.randint(1, 5)
                    progression = "\n".join([f"🏇 | {'➖' * pistes[p]} {p}" for p in pistes])
                    await i.edit_original_response(content=f"🏁 **LA COURSE EST EN COURS !**\n\n{progression}")

                # Résultat
                gagnant = random.choice(self.participants)
                cagnotte = self.mise * len(self.participants)
                self.cog.update_money(gagnant.id, cagnotte)

                res = discord.Embed(
                    title="🏆 RÉSULTAT DE LA COURSE",
                    description=f"Le cheval de **{gagnant.mention}** franchit la ligne en premier !\n\n💰 Il rafle toute la mise : **{self.cog.fmt(cagnotte)} €** !",
                    color=0xF1C40F
                )
                await i.edit_original_response(content=None, embed=res)

        view = CourseView(self, interaction.user, mise)
        await interaction.response.send_message(embed=embed, view=view)

# ==================== PFC DUEL (Version SQLite) ====================
    @group.command(name="pfc", description="⚔️ Duel Pierre-Feuille-Ciseaux contre un autre joueur")
    async def pfc(self, interaction: discord.Interaction, adversaire: discord.Member, mise: int):
        if adversaire.id == interaction.user.id or adversaire.bot:
            return await interaction.response.send_message("❌ Action impossible.", ephemeral=True)

        u1_solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 1, 15000, u1_solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        u2_solde = self.get_user(adversaire.id)
        if u2_solde < mise:
            return await interaction.response.send_message(f"❌ **{adversaire.display_name}** n'a pas assez d'argent.", ephemeral=True)

        embed = discord.Embed(
            title="⚔️ INVITATION AU DUEL", 
            description=f"{interaction.user.mention} défie {adversaire.mention} !\n💰 Enjeu : **{self.fmt(mise)} €**", 
            color=0xF1C40F
        )

        class PFCInvite(discord.ui.View):
            def __init__(self, cog, p1, p2, mise):
                super().__init__(timeout=60)
                self.cog, self.p1, self.p2, self.mise = cog, p1, p2, mise

            @discord.ui.button(label="Accepter", emoji="⚔️", style=discord.ButtonStyle.success)
            async def accept(self, i: discord.Interaction, b):
                if i.user.id != self.p2.id: return await i.response.send_message("❌ Pas pour toi.", ephemeral=True)
                
                # Prélèvement des mises
                self.cog.update_money(self.p1.id, -self.mise)
                self.cog.update_money(self.p2.id, -self.mise)
                
                await i.response.edit_message(content="🎮 Le duel commence ! Choisissez votre arme...", embed=None, view=PFCGame(self.cog, self.p1, self.p2, self.mise))

            @discord.ui.button(label="Refuser", emoji="🚫", style=discord.ButtonStyle.danger)
            async def deny(self, i: discord.Interaction, b):
                if i.user.id != self.p2.id: return await i.response.send_message("❌ Pas pour toi.", ephemeral=True)
                await i.response.edit_message(content="❌ Duel refusé.", embed=None, view=None)

        class PFCGame(discord.ui.View):
            def __init__(self, cog, p1, p2, mise):
                super().__init__(timeout=60)
                self.cog, self.p1, self.p2, self.mise = cog, p1, p2, mise
                self.choices = {p1.id: None, p2.id: None}

            async def check_results(self, i):
                c1, c2 = self.choices[self.p1.id], self.choices[self.p2.id]
                if c1 and c2:
                    win_map = {"pierre": "ciseaux", "feuille": "pierre", "ciseaux": "feuille"}
                    res = discord.Embed(title="⚔️ RÉSULTAT DU DUEL", color=0x5865F2)
                    res.description = f"{self.p1.display_name} : **{c1}**\n{self.p2.display_name} : **{c2}**\n\n"
                    
                    if c1 == c2:
                        self.cog.update_money(self.p1.id, self.mise)
                        self.cog.update_money(self.p2.id, self.mise)
                        res.title = "🤝 ÉGALITÉ"; res.description += "Les mises sont rendues."
                    elif win_map[c1] == c2:
                        self.cog.update_money(self.p1.id, self.mise * 2)
                        res.title = f"🏆 {self.p1.display_name} GAGNE !"; res.description += f"Il remporte **{self.cog.fmt(self.mise*2)} €**"
                    else:
                        self.cog.update_money(self.p2.id, self.mise * 2)
                        res.title = f"🏆 {self.p2.display_name} GAGNE !"; res.description += f"Il remporte **{self.cog.fmt(self.mise*2)} €**"
                    
                    await i.edit_original_response(embed=res, view=None)

            async def make_choice(self, i, choice):
                if i.user.id not in self.choices: return await i.response.send_message("❌ Pas ton duel.", ephemeral=True)
                if self.choices[i.user.id]: return await i.response.send_message("✅ Déjà choisi !", ephemeral=True)
                self.choices[i.user.id] = choice
                await i.response.send_message(f"Tu as choisi {choice} !", ephemeral=True)
                await self.check_results(i)

            @discord.ui.button(label="Pierre", emoji="🪨")
            async def pierre(self, i, b): await self.make_choice(i, "pierre")
            @discord.ui.button(label="Feuille", emoji="🍃")
            async def feuille(self, i, b): await self.make_choice(i, "feuille")
            @discord.ui.button(label="Ciseaux", emoji="✂️")
            async def ciseaux(self, i, b): await self.make_choice(i, "ciseaux")

        await interaction.response.send_message(embed=embed, view=PFCInvite(self, interaction.user, adversaire, mise))

    # ==================== ROUE DE LA FORTUNE ====================
    @group.command(name="roue", description="🎡 Tourne la roue pour multiplier ta mise !")
    async def roue(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(pari, 5, 2000, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        await interaction.response.send_message("🎡 La roue tourne...")
        await asyncio.sleep(2)

        outcomes = [0, 0, 0.5, 1.5, 2, 5] # 0 = Perdu, 0.5 = Moitié rendu, etc.
        mult = random.choice(outcomes)
        
        if mult > 1:
            gain = round(pari * mult)
            self.update_money(interaction.user.id, gain)
            msg = f"✨ INCROYABLE ! La roue s'arrête sur **x{mult}**. Tu gagnes **{self.fmt(gain)} €** !"
        elif mult == 0:
            self.update_money(interaction.user.id, -pari)
            msg = f"💀 Aïe... La roue s'arrête sur **0**. Tu perds ta mise de **{self.fmt(pari)} €**."
        else:
            perte = round(pari * (1 - mult))
            self.update_money(interaction.user.id, -perte)
            msg = f"⚖️ Moyen... La roue s'arrête sur **x{mult}**. Tu récupères seulement la moitié."

        await interaction.edit_original_response(content=msg)

    # ==================== BLACKJACK (21) ====================
    @group.command(name="blackjack", description="🃏 Tente de te rapprocher de 21 sans dépasser !")
    async def blackjack(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(pari, 10, 5000, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        player_cards = [random.randint(1, 11), random.randint(1, 11)]
        dealer_cards = [random.randint(1, 11)]

        embed = discord.Embed(title="🃏 BLACKJACK", color=0x2C3E50)
        embed.add_field(name="Tes cartes", value=f"{player_cards} (Total: **{sum(player_cards)}**)", inline=False)
        embed.add_field(name="Banque", value=f"{dealer_cards} + ❓", inline=False)

        class BJView(discord.ui.View):
            def __init__(self, cog, p_cards, d_cards, mise):
                super().__init__(timeout=30)
                self.cog, self.p, self.d, self.m = cog, p_cards, d_cards, mise

            @discord.ui.button(label="Tirer", style=discord.ButtonStyle.green)
            async def hit(self, i, b):
                self.p.append(random.randint(1, 11))
                total = sum(self.p)
                if total > 21:
                    self.cog.update_money(i.user.id, -self.m)
                    await i.response.edit_message(content=f"💥 **BUST !** Tu as dépassé 21 ({total}). Perdu : -{self.cog.fmt(self.m)} €", embed=None, view=None)
                else:
                    new_embed = discord.Embed(title="🃏 BLACKJACK", description=f"Total actuel : **{total}**", color=0x2C3E50)
                    await i.response.edit_message(embed=new_embed)

            @discord.ui.button(label="Rester", style=discord.ButtonStyle.red)
            async def stay(self, i, b):
                while sum(self.d) < 17: self.d.append(random.randint(1, 11))
                pt, dt = sum(self.p), sum(self.d)
                if dt > 21 or pt > dt:
                    gain = self.m
                    self.cog.update_money(i.user.id, gain)
                    msg = f"✅ GAGNÉ ! La banque a {dt}. Tu gagnes **{self.cog.fmt(gain)} €**"
                elif pt == dt:
                    msg = "🤝 ÉGALITÉ ! Mise rendue."
                else:
                    self.cog.update_money(i.user.id, -self.m)
                    msg = f"❌ PERDU ! La banque a {dt}. Perte : -{self.cog.fmt(self.m)} €"
                await i.response.edit_message(content=msg, embed=None, view=None)

        await interaction.response.send_message(embed=embed, view=BJView(self, player_cards, dealer_cards, pari))

# ==================== PILE OU FACE (Version SQLite) ====================
    @group.command(name="pileouface", description="🪙 Tente le 50/50 (Max 7,500€)")
    async def pf(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        
        # Correction du crash : la fonction check_mise est maintenant reconnue
        err = self.check_mise(pari, 1, 7500, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        embed = discord.Embed(
            title="🪙 PILE OU FACE", 
            description="La pièce est lancée... Fais ton choix !", 
            color=0xF39C12
        )
        embed.add_field(name="💰 Mise engagée", value=f"`{self.fmt(pari)} €`", inline=True)
        embed.add_field(name="✨ Gain potentiel", value=f"`{self.fmt(round(pari*1.75))} €`", inline=True)

        class PFView(discord.ui.View):
            def __init__(self, cog, pari):
                super().__init__(timeout=30)
                self.cog = cog
                self.pari = pari

            async def play(self, i: discord.Interaction, choix: str):
                if i.user.id != interaction.user.id:
                    return await i.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)

                resultat = random.choice(["pile", "face"])
                emoji_resultat = "🟡" if resultat == "pile" else "⚪"
                
                res_embed = discord.Embed(
                    title="🪙 RÉSULTAT", 
                    description=f"La pièce s'arrête sur... {emoji_resultat} **{resultat.upper()}**", 
                    color=0xF39C12
                )

                if choix == resultat:
                    gain = round(self.pari * 1.75)
                    self.cog.update_money(i.user.id, gain)
                    res_embed.title = "💰 GAGNÉ !"; res_embed.color = 0x2ECC71
                    res_embed.add_field(name="Résultat", value=f"Bien vu ! Tu remportes **{self.cog.fmt(gain)} €**")
                else:
                    self.cog.update_money(i.user.id, -self.pari)
                    res_embed.title = "❌ PERDU"; res_embed.color = 0xE74C3C
                    res_embed.add_field(name="Résultat", value=f"Pas de chance. Tu perds **{self.cog.fmt(self.pari)} €**")

                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="PILE", emoji="🟡", style=discord.ButtonStyle.primary)
            async def pile(self, i, b): await self.play(i, "pile")

            @discord.ui.button(label="FACE", emoji="⚪", style=discord.ButtonStyle.secondary)
            async def face(self, i, b): await self.play(i, "face")

        await interaction.response.send_message(embed=embed, view=PFView(self, pari))

# ==================== CONNECTE 4 (2 JOUEURS) ====================
    @group.command(name="connecte4", description="🔴 Défie un ami au Puissance 4 ! (Mise partagée)")
    async def connecte4(self, interaction: discord.Interaction, mise: int):
        solde = self.get_user(interaction.user.id)
        if mise < 10: return await interaction.response.send_message("❌ Mise minimale : 10 €.", ephemeral=True)
        if solde < mise: return await interaction.response.send_message("❌ Tu n'as pas assez d'argent.", ephemeral=True)

        embed = discord.Embed(
            title="🔴 CONNECTE 4 : DÉFI LANCÉ !",
            description=f"**{interaction.user.display_name}** mise **{self.fmt(mise)} €** !\nQui accepte le duel ?",
            color=0xe74c3c
        )

        class C4View(discord.ui.View):
            def __init__(self, cog, p1, mise):
                super().__init__(timeout=60)
                self.cog = cog
                self.p1 = p1
                self.p2 = None
                self.mise = mise
                self.board = [[0]*7 for _ in range(6)] # 0: vide, 1: P1 (🔴), 2: P2 (🟡)
                self.turn = p1
                self.game_active = False

            def get_board_str(self):
                symbols = {0: "⚪", 1: "🔴", 2: "🟡"}
                txt = ""
                for row in self.board:
                    txt += "".join([symbols[cell] for cell in row]) + "\n"
                return txt + "1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣"

            def check_win(self, p):
                # Horizontal
                for r in range(6):
                    for c in range(4):
                        if all(self.board[r][c+i] == p for i in range(4)): return True
                # Vertical
                for r in range(3):
                    for c in range(7):
                        if all(self.board[r+i][c] == p for i in range(4)): return True
                # Diagonal /
                for r in range(3, 6):
                    for c in range(4):
                        if all(self.board[r-i][c+i] == p for i in range(4)): return True
                # Diagonal \
                for r in range(3):
                    for c in range(4):
                        if all(self.board[r+i][c+i] == p for i in range(4)): return True
                return False

            @discord.ui.button(label="REJOINRE LE DUEL", style=discord.ButtonStyle.green)
            async def join(self, i: discord.Interaction, b: discord.ui.Button):
                if i.user.id == self.p1.id: return await i.response.send_message("❌ Tu ne peux pas jouer contre toi-même !", ephemeral=True)
                s2 = self.cog.get_user(i.user.id)
                if s2 < self.mise: return await i.response.send_message("❌ Tu n'as pas assez d'argent !", ephemeral=True)
                
                self.p2 = i.user
                self.game_active = True
                self.cog.update_money(self.p1.id, -self.mise)
                self.cog.update_money(self.p2.id, -self.mise)
                
                self.clear_items()
                for n in range(1, 8):
                    btn = discord.ui.Button(label=str(n), custom_id=str(n-1), style=discord.ButtonStyle.blurple)
                    btn.callback = self.play_move
                    self.add_item(btn)
                
                emb = discord.Embed(title="🎮 MATCH EN COURS", description=f"🔴 {self.p1.mention} vs 🟡 {self.p2.mention}\n\n{self.get_board_str()}", color=0x3498db)
                emb.set_footer(text=f"Tour de : {self.turn.display_name}")
                await i.response.edit_message(embed=emb, view=self)

            async def play_move(self, i: discord.Interaction):
                if i.user.id != self.turn.id: return await i.response.send_message("❌ Ce n'est pas ton tour !", ephemeral=True)
                col = int(i.data['custom_id'])
                
                # Placer le jeton
                row_placed = -1
                for r in range(5, -1, -1):
                    if self.board[r][col] == 0:
                        self.board[r][col] = 1 if i.user.id == self.p1.id else 2
                        row_placed = r
                        break
                
                if row_placed == -1: return await i.response.send_message("❌ Colonne pleine !", ephemeral=True)
                
                p_num = 1 if i.user.id == self.p1.id else 2
                if self.check_win(p_num):
                    pot = self.mise * 2
                    self.cog.update_money(i.user.id, pot)
                    emb = discord.Embed(title="🏆 VICTOIRE !", description=f"**{i.user.display_name}** a gagné le pot de **{self.cog.fmt(pot)} €** !\n\n{self.get_board_str()}", color=0x2ecc71)
                    return await i.response.edit_message(embed=emb, view=None)

                # Switch turn
                self.turn = self.p2 if self.turn == self.p1 else self.p1
                emb = discord.Embed(title="🎮 MATCH EN COURS", description=f"🔴 {self.p1.mention} vs 🟡 {self.p2.mention}\n\n{self.get_board_str()}", color=0x3498db)
                emb.set_footer(text=f"Tour de : {self.turn.display_name}")
                await i.response.edit_message(embed=emb, view=self)

        view = C4View(self, interaction.user, mise)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Jeux(bot))
