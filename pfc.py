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
