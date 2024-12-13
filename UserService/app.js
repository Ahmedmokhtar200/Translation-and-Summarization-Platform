require('dotenv').config();
const express = require('express');
const app = express();
const port = process.env.PORT || 3000;
const cors = require('cors');

const supertokens = require("supertokens-node");
const Session = require("supertokens-node/recipe/session");
let ThirdParty = require("supertokens-node/recipe/thirdparty");
const { middleware } = require("supertokens-node/framework/express");
const { verifySession } = require("supertokens-node/recipe/session/framework/express");
const { sessionRequest } = require("supertokens-node/framework/express");
const EmailPassword = require("supertokens-node/recipe/emailpassword");

// oauth authentication provider 
supertokens.init({
    framework: "express",
    supertokens: {
        // https://try.supertokens.com is for demo purposes. Replace this with the address of your core instance (sign up on supertokens.com), or self host a core.
        // supertoken host
        connectionURI: "http://supertokens:3567",
        // apiKey: <API_KEY(if configured)>,
    },
    appInfo: {
        // learn more about this on https://supertokens.com/docs/session/appinfo
        appName: "AuthenticationService",
        // api -> backend
        apiDomain: "http://localhost:5000",
        // website -> frontend
        websiteDomain: "http://localhost:5173",
        apiBasePath: "/auth",
        websiteBasePath: "/auth"
    },
    recipeList: [
        ThirdParty.init({
            signInAndUpFeature: {
                // We have provided you with development keys which you can use for testing.
                // IMPORTANT: Please replace them with your own OAuth keys for production use.
                providers: [{
                    config: {
                        thirdPartyId: "google",
                        clients: [{
                            clientId: "1007078620709-16rnj0l6j3carbtsu1pnbfum3k6a02tk.apps.googleusercontent.com",
                            clientSecret: "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"
                        }]
                    }
                }],
            }
        }),
        Session.init(), // initializes session features
        EmailPassword.init({
            
        }),
        // DashboardError.init({

        // })
    ]
});


app.use(cors({
    origin: "http://localhost:5173",
    allowedHeaders: ["content-type", ...supertokens.getAllCORSHeaders()],
    credentials: true,
}));

app.use(express.json());
// IMPORTANT: CORS should be before the below line.
app.use(middleware());

app.post("/auth/signin", async (req, res) => {
    try {
        const userId = req.body.userId; // Extract userId from the request

        // Check if the user exists in the database
        const result = await pool.query("SELECT * FROM user WHERE user_id = $1", [userId]);

        if (result.rows.length === 0) {
            // If user doesn't exist, insert new record
            await pool.query(
                "INSERT INTO user (user_id, email, created_at) VALUES ($1, $2, NOW())",
                [userId, req.body.email]
            );
        }

        res.status(200).json({ message: "User login successfully" });
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: "Error storing user data" });
    }
});

app.post("/like", verifySession(), (req, res) => {
    const userId = req.session.getUserId();
    // Your code logic here...
    res.send("Comment liked!"); // Example response
});

app.listen(port,()=>{
    console.log(`Server is running at port ${port}`)
})