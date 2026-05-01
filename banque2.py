import discord
from discord import app_commands
from discord.ext import commands
import time
import asyncio
import random

class Banque2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Plus besoin de db_file car on utilise self.bot.db du main.py

    def get_user(self, user_id):
        """Récupère l'utilisateur en base SQLite et gère le revenu passif"""
        cursor = self.bot.db.cursor()
        
        # S'assurer que les colonnes secours existent dans ta table SQLite (voir mon message plus bas)
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, money, banque, entreprise_secours, last_secours_payout, last_secours_claim) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, 100, 0, 0, 0, 0))
        self.bot.db.commit()

        cursor.execute("SELECT money, banque, entreprise_secours, last_secours_payout, last_secours_claim FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        u = {
            "portefeuille": row[0],
            "banque": row[1],
            "entreprise_secours": row[2],
            "last_secours_payout": row[3],
            "last_secours_claim": row[4]
        }

        # --- LOGIQUE DE REVENU PASSIF (Toutes les 30 min) ---
        valeur_ent = u["entreprise_secours"]
        if valeur_ent > 0:
            maintenant = time.time()
            derniere_paie = u["last_secours_payout"]
            if derniere_paie == 0: derniere_paie = maintenant
            
            nb_paies = int((maintenant - derniere_paie) // 1800)
            if nb_paies > 0:
                gain_total = nb_paies * valeur_ent
                u["portefeuille"] += gain_total
                u["last_secours_payout"] = derniere_paie + (nb_paies * 1800)
                
                # On sauvegarde immédiatement ce gain passif
                cursor.execute("UPDATE users SET money = ?, last_secours_payout = ? WHERE user_id = ?", 
                               (u["portefeuille"], u["last_secours_payout"], user_id))
                self.bot.db.commit()
        
        return u

    def save_user(self, user_id, u):
        """Sauvegarde les données dans SQLite"""
        cursor = self.bot.db.cursor()
        cursor.execute('''
            UPDATE users SET money = ?, banque = ?, entreprise_secours = ?, 
            last_secours_payout = ?, last_secours_claim = ? 
            WHERE user_id = ?
        ''', (u["portefeuille"], u["banque"], u["entreprise_secours"], 
              u["last_secours_payout"], u["last_secours_claim"], user_id))
        self.bot.db.commit()

    group = app_commands.Group(name="banque", description="🏦 Services bancaires secondaires")

    # --- COMMANDE PAYER ---
    @group.command(name="payer", description="Envoyer de l'argent (Minimum 1€)")
    async def payer(self, interaction: discord.Interaction, cible: discord.Member, montant: int):
        if montant < 1: 
            return await interaction.response.send_message("❌ Tu ne peux pas envoyer moins de `1 €` !", ephemeral=True)
        
        if cible.id == interaction.user.id:
            return await interaction.response.send_message("❌ Tu ne peux pas t'envoyer de l'argent à toi-même.", ephemeral=True)

        u1 = self.get_user(interaction.user.id)
        u2 = self.get_user(cible.id)

        if u1["portefeuille"] < montant:
            return await interaction.response.send_message(f"❌ Pas assez de cash !", ephemeral=True)

        u1["portefeuille"] -= montant
        u2["portefeuille"] += montant
        
        self.save_user(interaction.user.id, u1)
        self.save_user(cible.id, u2)

        embed = discord.Embed(
            title="💸 TRANSFERT RÉUSSI",
            description=f"Tu as envoyé **`{montant:,} €`** à {cible.mention}.".replace(',', ' '),
            color=0x2ecc71
        )
        embed.add_field(name="💵 Portefeuille", value=f"`{u1['portefeuille']:,} €`".replace(',', ' '), inline=True)
        embed.add_field(name="🏛️ Banque", value=f"`{u1['banque']:,} €`".replace(',', ' '), inline=True)
        embed.add_field(name="💳 Nouveau Total", value=f"**`{u1['portefeuille'] + u1['banque']:,} €`**".replace(',', ' '), inline=False)
        await interaction.response.send_message(embed=embed)

    # --- COMMANDE SECOURS (CONDITION < 10 000€) ---
    @group.command(name="secours", description="Obtenir une entreprise (Si total < 10 000€ | 14 jours)")
    async def secours(self, interaction: discord.Interaction):
        u = self.get_user(interaction.user.id)
        
        total = u["portefeuille"] + u["banque"]
        if total >= 10000:
            return await interaction.response.send_message(f"❌ La banque de secours n'aide que les joueurs ayant moins de `10 000 €`. (Tu as `{total:,} €`)".replace(',', ' '), ephemeral=True)

        now = time.time()
        last_claim = u["last_secours_claim"]
        if now - last_claim < 1209600:
            jours = (1209600 - (now - last_claim)) // 86400
            return await interaction.response.send_message(f"⏳ Tu as déjà utilisé la roue de secours. Reviens dans `{int(jours)}` jours.", ephemeral=True)

        class SecoursView(discord.ui.View):
            def __init__(self, cog, uid):
                super().__init__(timeout=60)
                self.cog, self.uid = cog, uid

            @discord.ui.button(label="🎰 Tourner la roue", style=discord.ButtonStyle.primary)
            async def spin(self, i: discord.Interaction, button: discord.ui.Button):
                if i.user.id != self.uid:
                    return await i.response.send_message("❌ Ce n'est pas ta roue !", ephemeral=True)
                
                self.stop()
                await i.response.edit_message(content="🎡 **La roue tourne...**", view=None)
                
                msg = await i.original_response()
                for _ in range(5):
                    await msg.edit(content=f"🎡 **La roue tourne :** [ {random.randint(5, 50)}€ ]")
                    await asyncio.sleep(0.4)

                gain = random.randint(5, 50)
                usr = self.cog.get_user(self.uid)
                usr["entreprise_secours"] = gain
                usr["last_secours_claim"] = time.time()
                usr["last_secours_payout"] = time.time()
                self.cog.save_user(self.uid, usr)

                embed = discord.Embed(
                    title="🏢 ENTREPRISE DE SECOURS",
                    description=f"La roue s'est arrêtée ! Tu as gagné une entreprise qui rapporte :\n\n💰 **`{gain} €` toutes les 30 minutes.**",
                    color=0x9b59b6
                )
                embed.set_footer(text="Revenu passif activé.")
                await msg.edit(content=None, embed=embed)

        await interaction.response.send_message(
            content="🚑 **AIDE FINANCIÈRE**\nTon total est inférieur à 10 000 €, tu es éligible à une entreprise de secours.",
            view=SecoursView(self, interaction.user.id)
        )

async def setup(bot):
    await bot.add_cog(Banque2(bot))
